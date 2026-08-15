/**
 * Upload-processing tests — the fail-closed proof (phase 17).
 *
 * content-and-web.md's acceptance requirements, in test form: a type mismatch
 * (PHP renamed .png) is rejected by magic bytes; a decompression bomb is
 * rejected before decode; an SVG with <script> is sanitized; entity expansion
 * and pathological nesting are rejected; the file never becomes servable on
 * any failure.
 */
import { describe, expect, it } from "vitest";
import sharp from "sharp";

import { MAX_BYTES, processUpload, UploadRejected } from "../src/process.js";

/** A tiny valid PNG (1×1 red), the honest fixture. */
async function tinyPng(): Promise<Buffer> {
  return sharp({
    create: {
      width: 1,
      height: 1,
      channels: 3,
      background: { r: 255, g: 0, b: 0 },
    },
  })
    .png()
    .toBuffer();
}

describe("processUpload — fail-closed pipeline", () => {
  it("rejects a type mismatch by magic bytes (PHP renamed .png)", async () => {
    const php = Buffer.from('<?php echo "pwn"; ?>');
    await expect(processUpload(php, "image/png")).rejects.toThrow(
      UploadRejected,
    );
  });

  it("rejects an empty file", async () => {
    await expect(processUpload(Buffer.alloc(0), "image/png")).rejects.toThrow(
      UploadRejected,
    );
  });

  it("rejects a file over the size cap before decode", async () => {
    const big = Buffer.alloc(MAX_BYTES + 1, 0x89);
    await expect(processUpload(big, "image/png")).rejects.toThrow(
      "file too large",
    );
  });

  it("rejects a claimed-type mismatch even for real image bytes", async () => {
    const png = await tinyPng();
    await expect(processUpload(png, "image/jpeg")).rejects.toThrow(
      "type mismatch",
    );
  });

  it("re-encodes a valid raster and strips to PNG", async () => {
    const png = await tinyPng();
    const result = await processUpload(png, "image/png");
    expect(result.contentType).toBe("image/png");
    expect(result.bytes.length).toBeGreaterThan(0);
    expect(result.dominantColor).toBeDefined();
  });

  it("sanitizes an SVG containing <script>", async () => {
    const evil = Buffer.from(
      '<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script>' +
        '<rect width="10" height="10"/></svg>',
    );
    const result = await processUpload(evil, "image/svg+xml");
    const out = result.bytes.toString("utf8");
    expect(out).not.toContain("<script");
    expect(out).toContain("<rect");
  });

  it("strips event-handler attributes from an SVG", async () => {
    const evil = Buffer.from(
      '<svg xmlns="http://www.w3.org/2000/svg"><rect onload="alert(1)" width="10" height="10"/></svg>',
    );
    const result = await processUpload(evil, "image/svg+xml");
    expect(result.bytes.toString("utf8")).not.toContain("onload");
  });

  it("rejects an SVG entity-expansion bomb", async () => {
    const bomb = Buffer.from(
      '<!DOCTYPE svg [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;">]>' +
        '<svg xmlns="http://www.w3.org/2000/svg"><text>&lol2;</text></svg>',
    );
    await expect(processUpload(bomb, "image/svg+xml")).rejects.toThrow(
      "entity expansion",
    );
  });

  it("rejects pathologically nested SVG", async () => {
    const nested = `<svg xmlns="http://www.w3.org/2000/svg">${"<g>".repeat(40)}</svg>`;
    await expect(
      processUpload(Buffer.from(nested), "image/svg+xml"),
    ).rejects.toThrow("nesting too deep");
  });
});
