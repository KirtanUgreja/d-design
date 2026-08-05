import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Brief } from '@/schema';

import { directBrief } from './direct';

const BRIEF: Brief = {
  goal: 'Launch a thing',
  audience: 'People who might buy it',
  keyMessages: ['It is fast', 'It is cheap', 'It is reliable'],
  proofPoints: [],
  tone: 'confident',
  cta: { label: 'Get started', href: 'https://example.com' },
  assets: [],
};

const OUTLINE_JSON = {
  title: 'A narrative',
  scenes: [
    { intent: 'hook', beat: 'open strong', layoutHint: 'centered' },
    { intent: 'problem', beat: 'name the pain', layoutHint: 'split-left' },
    { intent: 'cta', beat: 'ask for the click', layoutHint: 'centered' },
  ],
};

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('directBrief', () => {
  it('returns a parsed Outline on success', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000');
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(new Response(JSON.stringify(OUTLINE_JSON), { status: 200 })),
    );

    const result = await directBrief('exp-1', BRIEF);

    expect(result.ok).toBe(true);
    if (result.ok) expect(result.value.title).toBe('A narrative');
  });

  it('maps a 429 to quota_exceeded', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000');
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('over quota', { status: 429 })),
    );

    const result = await directBrief('exp-1', BRIEF);

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('quota_exceeded');
  });

  it('rejects a malformed response rather than returning it unvalidated', async () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000');
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ bogus: true }), { status: 200 }),
        ),
    );

    const result = await directBrief('exp-1', BRIEF);

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('invalid_input');
  });
});
