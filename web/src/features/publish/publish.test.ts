import { randomUUID } from 'node:crypto';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { deleteArtifact, readArtifact, writeArtifact } from '@/lib/storage';

import { embedHeaders, publishedHeaders } from './csp';
import { publishExperience, readPublishedArtifact, unpublishExperience } from './publish';

const MINIMAL_EXPERIENCE = {
  id: 'exp-1',
  title: 'Minimal Experience',
  mode: 'scroll',
  brandId: 'brand-1',
  artDirection: 'cinematic-dark',
  scenes: [
    {
      id: 's1',
      intent: 'hook',
      layout: 'centered',
      blocks: [{ id: 'b1', props: { type: 'headline', text: 'Ship the thing' } }],
    },
    {
      id: 's2',
      intent: 'problem',
      layout: 'centered',
      blocks: [
        { id: 'b2', props: { type: 'body', text: 'Most launches take too long.' } },
      ],
    },
    {
      id: 's3',
      intent: 'cta',
      layout: 'centered',
      blocks: [
        {
          id: 'b3',
          props: {
            type: 'cta',
            label: 'Start',
            href: 'https://example.com',
            style: 'primary',
          },
        },
      ],
    },
  ],
  meta: { createdAt: '2026-01-01T00:00:00Z', updatedAt: '2026-01-01T00:00:00Z' },
};

describe('CSP header sets', () => {
  it('published: connect-src none, frame-ancestors *', () => {
    const h = publishedHeaders();
    expect(h['Content-Security-Policy']).toContain("connect-src 'none'");
    expect(h['Content-Security-Policy']).toContain('frame-ancestors *');
  });

  it('embed: same as published — no second policy to drift', () => {
    expect(embedHeaders()).toEqual(publishedHeaders());
  });
});

describe('publish/unpublish', () => {
  let id: string;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    id = randomUUID();
  });

  afterEach(async () => {
    globalThis.fetch = originalFetch;
    await deleteArtifact(id);
  });

  it('writes the artifact and marks published on success', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(MINIMAL_EXPERIENCE), { status: 200 }),
      )
      .mockResolvedValueOnce(new Response('{}', { status: 200 }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await publishExperience(id);
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain(`/experiences/${id}/publish`);

    const artifact = await readPublishedArtifact(id);
    expect(artifact.ok).toBe(true);
    if (artifact.ok) expect(artifact.value.title).toBe('Minimal Experience');
  });

  it('fails closed when the experience is not found', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response('not found', { status: 404 }),
      ) as unknown as typeof fetch;

    const result = await publishExperience(id);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('not_found');

    const artifact = await readArtifact(id);
    expect(artifact.ok).toBe(false);
  });

  it('fails closed on a malformed upstream response', async () => {
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response('{"not":"an experience"}', { status: 200 }),
      ) as unknown as typeof fetch;

    const result = await publishExperience(id);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('invalid_input');
  });

  it('unpublish deletes the artifact so serving stops immediately', async () => {
    await writeArtifact(id, {
      title: 'x',
      mode: 'scroll',
      artDirection: 'cinematic-dark',
      scenes: [],
      publishedAt: new Date().toISOString(),
    });

    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response('{}', { status: 200 }),
      ) as unknown as typeof fetch;

    const result = await unpublishExperience(id);
    expect(result.ok).toBe(true);

    const artifact = await readArtifact(id);
    expect(artifact.ok).toBe(false);
  });
});

describe('readPublishedArtifact', () => {
  it('rejects a corrupted artifact rather than crashing the page', async () => {
    const id = randomUUID();
    await writeArtifact(id, { garbage: true });
    const result = await readPublishedArtifact(id);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('invalid_input');
    await deleteArtifact(id);
  });
});
