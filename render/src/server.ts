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

import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';
import { fromMotionRecord, fromRecord } from '@/features/art-direction';
import {
  artDirectionRecordSchema,
  motionVocabularyRecordSchema,
  sceneSchema,
} from '@/schema';

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
  artDirection: unknown;
  motionVocabulary: unknown;
  reducedMotion?: unknown;
  viewport?: { width?: unknown; height?: unknown };
}

/** One parse, at entry, for everything crossing the process boundary — the
 * scene tree and the art-direction record, both through the generated Zod
 * validators.
 *
 * **The payload carries tokens now, and that is the change phase 01 forced.**
 * It used to carry an id checked against a closed set, which was the safer
 * shape while art directions were code: a payload of raw tokens is a payload
 * of CSS values, which is the injection surface rule 13 exists for. Art
 * directions became database rows in v2 phase 01 and this service holds no
 * credential — deliberately, because that is what makes running a browser next
 * to it safe — so it cannot resolve an id and an id is no longer a reference
 * to anything it can reach.
 *
 * What replaces the closed set is not trust. It is `artDirectionRecordSchema`,
 * the same generated validator `web` parses the same bytes with, whose every
 * leaf is a number or a closed union and which has no field a free-form CSS
 * string could arrive in. Phase 03's linter runs on the parsed result, exactly
 * as it will for a designer's uploaded token file. */
function parseRequest(raw: string): {
  scenes: ReturnType<typeof sceneSchema.parse>[];
  artDirection: ArtDirection;
  motion: { full: MotionVocabulary; reduced: MotionVocabulary };
  reducedMotion: boolean;
  viewport: { width: number; height: number };
} {
  const body = JSON.parse(raw) as ScreenshotRequest;

  if (!Array.isArray(body.scenes) || body.scenes.length === 0) {
    throw new Error('scenes must be a non-empty array');
  }
  const scenes = body.scenes.map((scene) => sceneSchema.parse(scene));

  // Required, with no default. A default art direction would be this service
  // holding an opinion about how a page looks, which is the one thing it must
  // not have — and a caller that forgot the field would get a screenshot of
  // somebody else's design and no indication anything was wrong.
  const record = artDirectionRecordSchema.parse(body.artDirection);
  const resolved = fromRecord(record);
  if (!resolved.ok)
    throw new Error(`art direction did not resolve: ${resolved.error.code}`);

  // The second axis, on the wire for the same reason as the first: motion is a
  // row now and this service holds no credential to read one with. Required
  // too — a default vocabulary would be this service deciding how a page moves.
  const motion = fromMotionRecord(
    motionVocabularyRecordSchema.parse(body.motionVocabulary),
  );

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
    artDirection: resolved.value.artDirection,
    motion,
    reducedMotion: body.reducedMotion !== false,
    viewport: { width: clamp(width), height: clamp(height) },
  };
}

/** What a scene actually measured, once a browser had laid it out.
 *
 * The whole reason this endpoint exists rather than a calculation in `api`:
 * whether copy fits is a question about line breaking, font metrics, clamped
 * type and the art direction's own frame, and nothing short of a real layout
 * engine answers it. Guessing from character counts is how a product tells a
 * customer their approved headline fits and then clips it.
 */
export interface SceneExtent {
  sceneId: string;
  /** The frame the art direction gave this scene — its `min-block-size` once
   * resolved, or the viewport when the layout runs at content height. */
  frameBlockSize: number;
  /** What the content actually needed. */
  contentBlockSize: number;
  blocks: { blockId: string; blockSize: number }[];
}

export async function measure(raw: string): Promise<SceneExtent[]> {
  const { scenes, artDirection, motion, reducedMotion, viewport } = parseRequest(raw);
  const html = renderDocument(scenes, artDirection, motion, reducedMotion);
  return withPage(viewport, async (page) => {
    await page.setContent(html, { waitUntil: 'domcontentloaded' });
    await page.evaluate(() => document.fonts.ready);
    return page.evaluate((frameHeight) => {
      return [...document.querySelectorAll('section[id^="scene-"]')].map((section) => {
        const el = section as HTMLElement;
        return {
          sceneId: el.id.replace(/^scene-/, ''),
          // The viewport, not the section's own height: a scene that grew past
          // the frame reports its *own* size as the frame otherwise, and every
          // overflow measures as zero. That inversion is the whole bug this
          // endpoint would ship with if the two were confused.
          frameBlockSize: frameHeight,
          contentBlockSize: el.scrollHeight,
          blocks: [...el.querySelectorAll('[data-block-id]')].map((node) => ({
            blockId: (node as HTMLElement).dataset.blockId ?? '',
            blockSize: Math.round((node as HTMLElement).getBoundingClientRect().height),
          })),
        };
      });
    }, viewport.height);
  });
}

export async function screenshot(raw: string): Promise<Buffer> {
  const { scenes, artDirection, motion, reducedMotion, viewport } = parseRequest(raw);
  const html = renderDocument(scenes, artDirection, motion, reducedMotion);
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
    // "payload", not "scene tree" — the art-direction record is parsed by the
    // same validator since phase 01, and naming the wrong half of the body
    // sends someone hunting through a scene tree that was fine.
    return `payload failed validation: ${[...new Set(seen)].join('; ')}`;
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
  // Two routes, one payload shape. `/measure` answers "does this fit" and
  // `/screenshot` answers "what does it look like"; both need a real layout,
  // which is the whole reason either lives in a service with a browser in it.
  if (req.method !== 'POST' || (req.url !== '/screenshot' && req.url !== '/measure')) {
    res.writeHead(404).end();
    return;
  }
  try {
    const body = await readBody(req);
    if (req.url === '/measure') {
      // Measured first, then the head — never the other way round. Writing a
      // 200 before the work that can fail means the `catch` below tries to
      // write a second set of headers, which throws `ERR_HTTP_HEADERS_SENT`
      // *outside* the promise and takes the whole process down: one malformed
      // request is a denial of service on every tenant sharing the service.
      //
      // Found by sending a payload with no `artDirection` once phase 01 made
      // the field required. The ordering was wrong before that too — any parse
      // failure would have done it — it simply had no reachable trigger while
      // the field had a default. `/screenshot` below already had it right,
      // which is what the two lines looking different was telling us.
      const extents = await measure(body);
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end(JSON.stringify(extents));
      return;
    }
    const png = await screenshot(body);
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
