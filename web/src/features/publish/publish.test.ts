import { randomUUID } from 'node:crypto';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { seededRecord } from '@/features/art-direction/server';
import { deleteArtifact, readArtifact, writeArtifact } from '@/lib/storage';
import { experienceSchema } from '@/schema';

import { embedHeaders, publishedHeaders } from './csp';
import {
  publishExperience,
  readPublishedArtifact,
  saveScenes,
  unpublishExperience,
} from './publish';

// The seeded record, as `api` would serve it — the second call publishing now
// makes. Art directions are rows since v2 phase 01, and the artifact freezes
// the tokens rather than a reference, which is what makes a published page
// unable to restyle itself (v2 rule 15).
const AD_RECORD = seededRecord('cinematic-dark');

const MINIMAL_EXPERIENCE = {
  id: 'exp-1',
  title: 'Minimal Experience',
  mode: 'scroll',
  brandId: 'brand-1',
  artDirection: { id: 'cinematic-dark', version: 1 },
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
      .mockResolvedValueOnce(new Response(JSON.stringify(AD_RECORD), { status: 200 }))
      .mockResolvedValueOnce(new Response('{}', { status: 200 }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    const result = await publishExperience(id);
    expect(result.ok).toBe(true);
    // Three: read the experience, resolve its art direction, mark published.
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(String(fetchMock.mock.calls[1]?.[0])).toContain(
      '/art-directions/cinematic-dark/1',
    );
    expect(String(fetchMock.mock.calls[2]?.[0])).toContain(`/experiences/${id}/publish`);

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
      artDirectionRef: { id: 'cinematic-dark', version: 1 },
      artDirection: AD_RECORD,
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

describe('saveScenes', () => {
  const originalFetch = globalThis.fetch;
  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('replaces only the scenes, carrying the stored fields through untouched', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(MINIMAL_EXPERIENCE), { status: 200 }),
      )
      .mockResolvedValueOnce(new Response('{}', { status: 200 }));
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    // Through the schema rather than cast: these are `Scene`s the same way the
    // editor's are, so the test cannot pass on a shape the real caller can't
    // produce.
    const scenes = experienceSchema.parse(MINIMAL_EXPERIENCE).scenes;
    const edited = scenes.map((scene, i) =>
      i === 0
        ? {
            ...scene,
            blocks: [
              { id: 'b1', props: { type: 'headline' as const, text: 'Ship it faster' } },
            ],
          }
        : scene,
    );

    const result = await saveScenes('exp-1', edited);
    expect(result.ok).toBe(true);

    // The whole point of the read-then-replace: `PUT` takes a full
    // `Experience`, so a client that assembled one from its own state would
    // silently reset title, mode and brand to whatever it happened to hold.
    const body: unknown = JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body));
    expect(body).toMatchObject({
      title: 'Minimal Experience',
      mode: 'scroll',
      brandId: 'brand-1',
      artDirection: { id: 'cinematic-dark', version: 1 },
    });
  });

  it('reports a rejected tree as invalid input, not as an outage', async () => {
    // 422 is what `api` returns when the *tree* rules fail — an edit that
    // deleted the last CTA, say. The editor has to be able to tell that apart
    // from the API being down, because only one of the two is the user's to fix.
    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify(MINIMAL_EXPERIENCE), { status: 200 }),
      )
      .mockResolvedValueOnce(
        new Response('an experience has at least one CTA', { status: 422 }),
      ) as unknown as typeof fetch;

    const result = await saveScenes(
      'exp-1',
      experienceSchema.parse(MINIMAL_EXPERIENCE).scenes,
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('invalid_input');
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
