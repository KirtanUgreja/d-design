// The client's controls: one parse at entry, and errors that stay actionable.
// The interview's own rules — the three always-ask fields, the claims check,
// the URL allowlist — are enforced and tested in `api`, and asserting them
// again here would be a second copy of a rule that has one owner.

import { afterEach, describe, expect, it, vi } from 'vitest';

import type { Brief } from '@/schema';

import { advanceInterview, loadBrief, saveBrief } from './intake';

const BRIEF: Brief = {
  goal: 'Launch our observability platform to engineering teams',
  audience: 'Backend engineers at mid-size SaaS companies',
  keyMessages: [
    'See every request across your whole stack in one trace',
    'Setup takes ten minutes with our existing SDKs',
    'It cuts mean time to resolution by 68%',
  ],
  proofPoints: ['cuts mean time to resolution by 68%'],
  tone: 'confident, technical',
  cta: { label: 'Start free trial', href: 'https://example.com/trial' },
  assets: [],
};

function respond(body: unknown, status = 200) {
  vi.stubEnv('NEXT_PUBLIC_API_URL', 'http://localhost:8000');
  const mock = vi
    .fn()
    .mockResolvedValue(
      new Response(typeof body === 'string' ? body : JSON.stringify(body), { status }),
    );
  vi.stubGlobal('fetch', mock);
  return mock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('advanceInterview', () => {
  it('returns the next question, with its progress counters', async () => {
    respond({
      question: { field: 'audience', text: 'Who is it for?', index: 2, total: 4 },
      brief: null,
    });

    const result = await advanceInterview('exp-1', { prompt: 'x', answers: {} });

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.question?.field).toBe('audience');
      expect(result.value.question?.index).toBe(2);
      expect(result.value.brief).toBeNull();
    }
  });

  it('returns the Brief when the interview is done', async () => {
    respond({ question: null, brief: BRIEF });

    const result = await advanceInterview('exp-1', { prompt: 'x', answers: {} });

    expect(result.ok).toBe(true);
    if (result.ok) expect(result.value.brief?.goal).toBe(BRIEF.goal);
  });

  it('rejects a malformed response rather than returning it unvalidated', async () => {
    respond({ question: { field: 'audience' }, brief: null });

    const result = await advanceInterview('exp-1', { prompt: 'x', answers: {} });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('invalid_input');
  });

  it("passes the api's message through, so a refusal reads as one", async () => {
    // 422 covers both `refused` and `invalid_input` on the wire, so the
    // message is what tells the user which happened. Losing it would leave
    // them with a failure they cannot act on.
    respond({ detail: 'the model declined the request' }, 422);

    const result = await advanceInterview('exp-1', { prompt: 'x', answers: {} });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.message).toBe('the model declined the request');
  });

  it('survives a non-JSON error body', async () => {
    respond('<html>502 Bad Gateway</html>', 502);

    const result = await advanceInterview('exp-1', { prompt: 'x', answers: {} });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.message).toContain('502');
  });

  it('maps a 429 to quota_exceeded', async () => {
    respond({ detail: 'over quota' }, 429);

    const result = await advanceInterview('exp-1', { prompt: 'x', answers: {} });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('quota_exceeded');
  });
});

describe('loadBrief', () => {
  it('returns not_found before the interview has produced one', async () => {
    respond({ detail: 'no brief for this experience yet' }, 404);

    const result = await loadBrief('exp-1');

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('not_found');
  });
});

describe('saveBrief', () => {
  it('round-trips a valid edit', async () => {
    const edited: Brief = { ...BRIEF, goal: 'Launch it to platform teams' };
    const fetchMock = respond(edited);

    const result = await saveBrief('exp-1', edited);

    expect(result.ok).toBe(true);
    if (result.ok) expect(result.value.goal).toBe('Launch it to platform teams');
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain('/experiences/exp-1/brief');
  });

  it('rejects a javascript: href without a round trip', async () => {
    // The reason the editor gets a generated Zod validator at all: `href`'s
    // scheme allowlist is a `Field(pattern=...)` on the Pydantic model, so it
    // crossed the codegen boundary and can be enforced offline
    // (docs/coderules/typescript.md).
    const fetchMock = respond(BRIEF);

    const result = await saveBrief('exp-1', {
      ...BRIEF,
      cta: { ...BRIEF.cta, href: 'javascript:alert(1)' },
    });

    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('invalid_input');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('rejects a sixth key message without a round trip', async () => {
    const fetchMock = respond(BRIEF);

    const result = await saveBrief('exp-1', {
      ...BRIEF,
      keyMessages: [...BRIEF.keyMessages, 'four', 'five', 'six'],
    });

    expect(result.ok).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
