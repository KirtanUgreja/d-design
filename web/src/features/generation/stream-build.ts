// The Build phase's SSE client (docs/v1/plan/06-model-seam-and-build.md ->
// "7. Streaming to the client"). Not a literal `new EventSource(...)`:
// `EventSource` is GET-only and this call needs a JSON body (`brief`,
// `outline`), so this reads the same `text/event-stream` wire format by hand
// over a POSTed `fetch` body instead. Runs in the browser, on purpose — the
// generation watch is a live thing the user watches assemble.

import { z } from 'zod';

import { sceneSchema, type Brief, type Outline, type Scene } from '@/schema';

export type GenerationEvent =
  | { type: 'scene'; index: number; scene: Scene }
  | { type: 'repair'; index: number }
  | { type: 'error'; index: number; code: string; message: string }
  | { type: 'done'; count: number };

const sceneEventSchema = z.strictObject({ index: z.number(), scene: sceneSchema });
const repairEventSchema = z.strictObject({ index: z.number() });
const errorEventSchema = z.strictObject({
  index: z.number(),
  code: z.string(),
  message: z.string(),
});
const doneEventSchema = z.strictObject({ count: z.number() });

function apiUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) throw new Error('NEXT_PUBLIC_API_URL is not set');
  return url;
}

/** One `event:`/`data:` frame -> a typed `GenerationEvent`. The payload
 * crosses the api/web boundary, so it gets the one parse every external
 * input gets (docs/coderules/typescript.md) — a malformed frame throws
 * rather than handing the caller an unvalidated `Scene`. */
function parseFrame(frame: string): GenerationEvent {
  const eventLine = frame.split('\n').find((l) => l.startsWith('event:'));
  const dataLine = frame.split('\n').find((l) => l.startsWith('data:'));
  if (!eventLine || !dataLine) {
    throw new Error(`malformed SSE frame: ${frame}`);
  }
  const type = eventLine.slice('event:'.length).trim();
  const data: unknown = JSON.parse(dataLine.slice('data:'.length).trim());

  switch (type) {
    case 'scene': {
      const p = sceneEventSchema.parse(data);
      return { type: 'scene', index: p.index, scene: p.scene };
    }
    case 'repair':
      return { type: 'repair', ...repairEventSchema.parse(data) };
    case 'error':
      return { type: 'error', ...errorEventSchema.parse(data) };
    case 'done':
      return { type: 'done', ...doneEventSchema.parse(data) };
    default:
      throw new Error(`unknown SSE event type: ${type}`);
  }
}

/** Splits a byte stream on blank-line-delimited SSE frames, tolerating a
 * frame split across two chunks — the one thing a naive per-chunk parse
 * gets wrong, since a chunk boundary has no relationship to a frame
 * boundary. */
export async function* streamBuild(
  experienceId: string,
  body: { brief: Brief; outline: Outline; brandId?: string },
  signal?: AbortSignal,
): AsyncGenerator<GenerationEvent> {
  const res = await fetch(`${apiUrl()}/experiences/${experienceId}/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`build stream failed: ${res.status} ${await res.text()}`);
  }

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let boundary = buffer.indexOf('\n\n');
    while (boundary !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      if (frame.trim()) yield parseFrame(frame);
      boundary = buffer.indexOf('\n\n');
    }
  }
}
