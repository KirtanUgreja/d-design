import { afterEach, describe, expect, it, vi } from 'vitest';

import { streamBuild } from './stream-build';

const SCENE_INPUT = {
  id: 's1',
  intent: 'hook',
  layout: 'centered',
  blocks: [{ id: 'b1', props: { type: 'headline', text: 'Ship the thing' } }],
};

// What Zod actually parses SCENE_INPUT into, defaults filled in — the same
// shape `sceneSchema.parse` produces inside `streamBuild`.
const SCENE = {
  id: 's1',
  intent: 'hook',
  layout: 'centered',
  notes: null,
  blocks: [
    {
      id: 'b1',
      region: null,
      motion: 'reveal',
      props: { type: 'headline', text: 'Ship the thing', emphasis: null },
    },
  ],
};

function sseResponse(chunks: string[]): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(new TextEncoder().encode(chunk));
      controller.close();
    },
  });
  return new Response(stream, { status: 200 });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('streamBuild', () => {
  it('parses scene, repair, error and done frames, split across chunks', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000');
    const frames =
      `event: repair\ndata: {"index":0}\n\n` +
      `event: scene\ndata: {"index":0,"scene":${JSON.stringify(SCENE_INPUT)}}\n\n` +
      `event: error\ndata: {"index":1,"code":"refused","message":"declined"}\n\n` +
      `event: done\ndata: {"count":1}\n\n`;
    // Split mid-frame, not on a frame boundary — the case a naive per-chunk
    // parse gets wrong.
    const mid = Math.floor(frames.length / 2);
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(sseResponse([frames.slice(0, mid), frames.slice(mid)])),
    );

    const events = [];
    for await (const event of streamBuild('exp-1', {
      brief: {
        goal: 'g',
        audience: 'a',
        keyMessages: ['a', 'b', 'c'],
        proofPoints: [],
        tone: 't',
        cta: { label: 'Go', href: 'https://example.com' },
        assets: [],
      },
      outline: {
        title: 'Outline',
        scenes: [
          { intent: 'hook', beat: 'open' },
          { intent: 'cta', beat: 'close' },
        ],
      },
    })) {
      events.push(event);
    }

    expect(events).toEqual([
      { type: 'repair', index: 0 },
      { type: 'scene', index: 0, scene: SCENE },
      { type: 'error', index: 1, code: 'refused', message: 'declined' },
      { type: 'done', count: 1 },
    ]);
  });

  it('throws on a malformed scene payload rather than yielding it unvalidated', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000');
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          sseResponse([`event: scene\ndata: {"index":0,"scene":{"bogus":true}}\n\n`]),
        ),
    );

    async function drain() {
      for await (const _ of streamBuild('exp-1', {
        brief: {
          goal: 'g',
          audience: 'a',
          keyMessages: ['a', 'b', 'c'],
          proofPoints: [],
          tone: 't',
          cta: { label: 'Go', href: 'https://example.com' },
          assets: [],
        },
        outline: { title: 'Outline', scenes: [{ intent: 'hook', beat: 'open' }] },
      })) {
        // draining
      }
    }
    await expect(drain()).rejects.toThrow();
  });
});
