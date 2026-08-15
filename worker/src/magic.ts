/**
 * Magic-byte verification (content-and-web.md: "Extension and Content-Type are
 * attacker-supplied").
 *
 * The worker checks the actual bytes, not the claimed type. A mismatch is a
 * rejection — this is the PHP-renamed-.png attack shape. The set here is the
 * types a brand kit may hold: PNG, JPEG, WEBP, GIF, SVG.
 */
import { fileTypeFromBuffer } from "file-type";

/** The image types the brand kit accepts, by file-type's detected mime. */
const ALLOWED = new Set([
  "image/png",
  "image/jpeg",
  "image/webp",
  "image/gif",
  "image/svg+xml",
]);

/**
 * Verify the bytes are one of the allowed image types. Returns the detected
 * mime, or null when the bytes are not an allowed image (or undetectable).
 * SVG detection is text-based (file-type detects the XML prolog / root tag).
 */
export async function detectImageType(bytes: Buffer): Promise<string | null> {
  if (bytes.length === 0) {
    return null;
  }
  const detected = await fileTypeFromBuffer(bytes);
  if (detected && ALLOWED.has(detected.mime)) {
    return detected.mime;
  }
  // file-type does not reliably classify SVG; the SVG signature as text is
  // the XML prolog, the root <svg>, or a leading DOCTYPE (which can carry
  // entity definitions — the sanitizer rejects those, but detection must
  // still recognize the file as SVG so the sanitizer gets to run).
  const head = bytes.subarray(0, 512).toString("utf8").trimStart();
  if (
    head.startsWith("<svg") ||
    head.startsWith("<?xml") ||
    head.startsWith("<!DOCTYPE")
  ) {
    return "image/svg+xml";
  }
  return null;
}
