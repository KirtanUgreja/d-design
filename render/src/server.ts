// One route: POST /screenshot.
//
// `node:http`, not a framework. One route with one method does not need a
// router, and this service's whole security story is that it is small enough
// to read (docs/coderules/dependencies.md — platform over dependency).
//
// **It holds no credential.** No database URL, no S3 key, no model key. That
// is what makes it safe to run a browser here at all, and it is asserted at
// startup below rather than left to the compose file to get right.
//
// **It is not the fetch worker and must never become it.** A schema-validated
// scene tree carrying no presentational values is *trusted* input; the fetch
// worker renders attackers' pages. Both run Chromium, which makes merging them
// look like a saving — it is the one merge the trust split forbids
// (docs/techstack/backend.md).

import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';

import type { ArtDirectionId } from '@/features/art-direction';
import { ART_DIRECTION_IDS } from '@/features/art-direction';
import { sceneSchema } from '@/schema';

import { withPage } from './browser';
import { renderDocument } from './render-scene';

// Credentials this process must never hold. Asserted at startup, because a
// control nobody checks is a comment — and the failure mode is silent: a
// `render` that acquired a DATABASE_URL works fine and has quietly collapsed
// the trust split that justified running a browser next to it.
const FORBIDDEN_ENV = [
  'DATABASE_URL',
  'MIGRATION_DATABASE_URL',
  'S3_ACCESS_KEY',
  'S3_SECRET_KEY',
  'OPENROUTER_API_KEY',
] as const;

export function assertNoCredentials(env: NodeJS.ProcessEnv = process.env): void {
  const held = FORBIDDEN_ENV.filter((name) => {
    const value = env[name];
    return value !== undefined && value !== '';
  });
  if (held.length > 0) {
    throw new Error(
      `render must hold no credential, but the environment carries: ${held.join(', ')}. ` +
        'See docs/techstack/backend.md — the trust split is why a browser runs here.',
    );
  }
}

/** The closed set the schema already declares — this service does not keep a
 * second list of which art directions exist. */
function isArtDirectionId(value: unknown): value is ArtDirectionId {
  return (
    typeof value === 'string' && (ART_DIRECTION_IDS as readonly string[]).includes(value)
  );
}

const MAX_BODY_BYTES = 2 * 1024 * 1024;
const DEFAULT_VIEWPORT = { width: 1280, height: 800 };

async function readBody(req: IncomingMessage): Promise<string> {
  const chunks: Buffer[] = [];
  let size = 0;
  for await (const chunk of req) {
    const buf = chunk as Buffer;
    size += buf.length;
    // Bounded during the read, not after it. A cap applied to an already
    // buffered body is not a cap.
    if (size > MAX_BODY_BYTES) throw new Error('payload too large');
    chunks.push(buf);
  }
  return Buffer.concat(chunks).toString('utf8');
}

interface ScreenshotRequest {
  scenes: unknown;
  artDirection?: unknown;
  reducedMotion?: unknown;
  viewport?: { width?: unknown; height?: unknown };
}

/** One parse, at entry, for everything crossing the process boundary — the
 * scene tree through Zod, and the art-direction id against the closed set the
 * schema already declares.
 *
 * The id rather than a token object, and that is a security choice as much as
 * a convenience: a payload carrying raw tokens is a payload carrying CSS
 * values, which is the injection surface rule 13 exists for. When phase 01
 * brings user-authored art directions, `jobs` will have to send tokens — and
 * they must arrive through the same validator phase 03 builds, never as a
 * trusted blob. */
function parseRequest(raw: string): {
  scenes: ReturnType<typeof sceneSchema.parse>[];
  artDirection: ArtDirectionId;
  reducedMotion: boolean;
  viewport: { width: number; height: number };
} {
  const body = JSON.parse(raw) as ScreenshotRequest;

  if (!Array.isArray(body.scenes) || body.scenes.length === 0) {
    throw new Error('scenes must be a non-empty array');
  }
  const scenes = body.scenes.map((scene) => sceneSchema.parse(scene));

  const artDirection = body.artDirection ?? ART_DIRECTION_IDS[0];
  if (!isArtDirectionId(artDirection)) {
    throw new Error(`unknown art direction: ${String(artDirection)}`);
  }

  const width = Number(body.viewport?.width ?? DEFAULT_VIEWPORT.width);
  const height = Number(body.viewport?.height ?? DEFAULT_VIEWPORT.height);
  if (!Number.isFinite(width) || !Number.isFinite(height)) {
    throw new Error('viewport must be numeric');
  }
  // Bounded: a viewport is a pixel buffer, and an unbounded one is a memory
  // cap expressed as a JSON field.
  const clamp = (n: number) => Math.min(Math.max(Math.round(n), 320), 4000);

  return {
    scenes,
    artDirection,
    reducedMotion: body.reducedMotion !== false,
    viewport: { width: clamp(width), height: clamp(height) },
  };
}

export async function screenshot(raw: string): Promise<Buffer> {
  const { scenes, artDirection, reducedMotion, viewport } = parseRequest(raw);
  const html = renderDocument(scenes, artDirection, reducedMotion);
  return withPage(viewport, async (page) => {
    // `setContent` rather than a data: URL or a temp file — no navigation, no
    // origin, nothing on disk. `networkidle` would hang forever on a page that
    // makes no requests, so this waits for the DOM and the fonts explicitly.
    await page.setContent(html, { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => document.fonts.ready);
    return page.screenshot({ type: 'png' });
  });
}

/** Which fields failed and how — never what they contained.
 *
 * A Zod error stringifies to the whole issue list, and an issue can carry the
 * offending value: for a scene tree that value is a customer's unreleased
 * launch copy, which never reaches a log or an error string
 * (docs/security/tenancy-and-data.md). The first version of this handler
 * returned `error.message` and shipped exactly that.
 *
 * Paths and codes only, which is the same trade the Python seam's `_describe`
 * already makes — enough to say "too_small at blocks", which is the sentence
 * that ends the debugging session, and nothing a caller did not already send.
 */
export function describeFailure(error: unknown): string {
  if (error !== null && typeof error === 'object' && 'issues' in error) {
    const issues = (error as { issues: { code?: string; path?: unknown[] }[] }).issues;
    const seen = issues
      .slice(0, 5)
      .map((i) => `${i.code ?? 'invalid'} at ${(i.path ?? []).join('.') || '(root)'}`);
    return `scene tree failed validation: ${[...new Set(seen)].join('; ')}`;
  }
  // Our own messages are written in this file and name no user data.
  return error instanceof Error ? error.message.slice(0, 200) : 'render failed';
}

async function handle(req: IncomingMessage, res: ServerResponse): Promise<void> {
  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end('{"ok":true}');
    return;
  }
  if (req.method !== 'POST' || req.url !== '/screenshot') {
    res.writeHead(404).end();
    return;
  }
  try {
    const png = await screenshot(await readBody(req));
    res.writeHead(200, {
      'content-type': 'image/png',
      'content-length': png.length,
    });
    res.end(png);
  } catch (error) {
    res.writeHead(400, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ error: describeFailure(error) }));
  }
}

if (process.env.NODE_ENV !== 'test') {
  assertNoCredentials();
  const port = Number(process.env.PORT ?? 3200);
  createServer((req, res) => {
    void handle(req, res);
  }).listen(port, () => {
    process.stdout.write(`render listening on ${String(port)}\n`);
  });
}
