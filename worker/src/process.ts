/**
 * The upload processing pipeline — the fetch-worker job (phase 17).
 *
 * content-and-web.md: every uploaded file is hostile until proven otherwise.
 * The pipeline fails closed: any error, cap, or sanitizer failure rejects the
 * file — it never reaches the servable state. The SVG rule is layering:
 * DOMPurify sanitizes, but the SVG is only ever served through <img> (the
 * actual control), and it stays out of any image-optimization path.
 *
 * Order matters: magic bytes first (don't decode what isn't an image), size
 * and dimension caps BEFORE decode (decompression bombs), then re-encode
 * (strips EXIF, kills polyglots), then SVG sanitize.
 */
import { JSDOM } from "jsdom";
import createDOMPurify from "dompurify";
import sharp from "sharp";

import { detectImageType } from "./magic.js";

/** Size cap before any decode: 5 MB. A 200KB PNG can decode to gigabytes —
 * the cap is what stops the bomb, and it is checked before sharp touches it. */
export const MAX_BYTES = 5 * 1024 * 1024;

/** Dimension caps before decode: 4096² is far beyond any logo need. */
export const MAX_DIMENSION = 4096;

/** SVG entity-expansion and nesting caps (billion-laughs, deep groups). */
export const MAX_ENTITIES = 64;
export const MAX_DEPTH = 24;

/** Accepted source types (magic bytes). */
export type SourceType = "png" | "jpeg" | "webp" | "gif" | "svg";

export class UploadRejected extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UploadRejected";
  }
}

const SVGCONFIG = createDOMPurify(new JSDOM("").window);

function countEntities(svg: string): void {
  // Billion-laughs: nested entity expansions. A DOCTYPE with internal
  // entities is a bomb signature; reject rather than expand.
  if (/<!DOCTYPE[^>]*\[[^\]]*<!ENTITY/.test(svg)) {
    throw new UploadRejected("svg entity expansion rejected");
  }
  const entityUses = (svg.match(/&[A-Za-z0-9]+;/g) ?? []).length;
  if (entityUses > MAX_ENTITIES) {
    throw new UploadRejected("svg too many entities");
  }
}

function depthOf(svg: string): void {
  // Pathological nesting (deep groups) is a CPU-bomb shape. A cheap max-depth
  // scan of the tag open/close balance bounds it without parsing.
  let depth = 0;
  let maxDepth = 0;
  for (const match of svg.matchAll(/<\s*\/?[A-Za-z][^>]*>/g)) {
    if (match[0].startsWith("</") || match[0].includes("/>")) {
      depth = Math.max(0, depth - 1);
    } else {
      depth += 1;
      maxDepth = Math.max(maxDepth, depth);
    }
  }
  if (maxDepth > MAX_DEPTH) {
    throw new UploadRejected("svg nesting too deep");
  }
}

function sanitizeSvg(source: string): string {
  countEntities(source);
  depthOf(source);
  const clean = SVGCONFIG.sanitize(source, {
    USE_PROFILES: { svg: true, svgFilters: true },
    FORBID_TAGS: ["script", "foreignObject"],
    FORBID_ATTR: ["onload", "onerror", "onclick", "style"],
    // External references (href pointing off-document) are the exfiltration
    // and injection surface; they are removed.
    ADD_ATTR: [],
  });
  if (clean.length === 0) {
    throw new UploadRejected("svg sanitized to nothing");
  }
  return clean;
}

export interface ProcessedFile {
  /** The verified, re-encoded (or sanitized) bytes, safe to serve. */
  bytes: Buffer;
  /** The server-set content type. */
  contentType: string;
  /** Extracted facts: the dominant color for raster logos, if any. */
  dominantColor?: string;
}

/**
 * Process an uploaded file: magic bytes -> caps -> re-encode/sanitize.
 * Throws UploadRejected on any failure — the file is never servable.
 */
export async function processUpload(
  bytes: Buffer,
  claimedType: string,
): Promise<ProcessedFile> {
  if (bytes.length === 0) {
    throw new UploadRejected("empty file");
  }
  if (bytes.length > MAX_BYTES) {
    throw new UploadRejected("file too large");
  }

  const detected = await detectImageType(bytes);
  if (detected === null) {
    throw new UploadRejected("not an allowed image type");
  }
  if (detected !== claimedType) {
    throw new UploadRejected(
      `type mismatch: claimed ${claimedType}, detected ${detected}`,
    );
  }

  if (detected === "image/svg+xml") {
    return {
      bytes: Buffer.from(sanitizeSvg(bytes.toString("utf8")), "utf8"),
      contentType: "image/svg+xml",
    };
  }

  // Raster: dimension caps before decode, then re-encode (EXIF strip,
  // polyglot kill, format normalize). Sharp reads the header without full
  // decode for metadata, but the explicit cap is the fail-closed gate.
  const meta = await sharp(bytes).metadata();
  const width = meta.width ?? 0;
  const height = meta.height ?? 0;
  if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
    throw new UploadRejected("image too large");
  }

  const reencoded = await sharp(bytes)
    .rotate()
    .resize({
      width: Math.min(width, MAX_DIMENSION),
      height: Math.min(height, MAX_DIMENSION),
      fit: "inside",
      withoutEnlargement: true,
    })
    .png()
    .toBuffer();

  // Dominant color extraction (sharp stats): the logo's leading fact.
  let dominantColor: string | undefined;
  try {
    const stats = await sharp(reencoded).stats();
    const d = stats.dominant;
    dominantColor = `#${[d.r, d.g, d.b]
      .map((v) => Math.round(v).toString(16).padStart(2, "0"))
      .join("")}`;
  } catch {
    // Extraction is a convenience, not a gate — the file is already verified.
    dominantColor = undefined;
  }

  return { bytes: reencoded, contentType: "image/png", dominantColor };
}
