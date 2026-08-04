// Visual judgment is a human check (docs/v1/plan/04-renderer.md — the review
// page is that surface, and "no snapshot tests" is explicit: a snapshot on a
// design surface fails on every intentional improvement). What this file
// proves instead: every primitive under every legal layout renders without
// throwing, in an environment with no DOM at all — the same shape of
// environment the job worker's renderToString runs in from v2 — plus the
// structural security assertions that must hold regardless of what anything
// looks like.

import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import {
  CINEMATIC_DARK,
  CINEMATIC_MOTION,
  REDUCED_MOTION,
} from '@/features/art-direction';
import { experienceSchema, sceneSchema } from '@/schema';

import { isSafeHref } from './blocks/href-safety';
import { SceneRenderer } from './scene-renderer';

const FIXTURES = join(process.cwd(), '..', 'api', 'schema', 'fixtures');
const readFixture = (name: string) =>
  experienceSchema.parse(
    JSON.parse(readFileSync(join(FIXTURES, `${name}.json`), 'utf8')),
  );

const FIXTURE_NAMES = ['minimal', 'full', 'hostile'] as const;
const LAYOUTS = [
  'full-bleed',
  'split-left',
  'split-right',
  'centered',
  'stack',
  'grid',
] as const;

describe('SceneRenderer', () => {
  for (const name of FIXTURE_NAMES) {
    it(`renders the ${name} fixture without throwing`, () => {
      const experience = readFixture(name);
      const html = renderToStaticMarkup(
        SceneRenderer({
          scenes: experience.scenes,
          artDirection: CINEMATIC_DARK,
          motion: CINEMATIC_MOTION,
        }),
      );
      expect(html.length).toBeGreaterThan(0);
    });

    it(`renders the ${name} fixture under REDUCED_MOTION without throwing`, () => {
      const experience = readFixture(name);
      const html = renderToStaticMarkup(
        SceneRenderer({
          scenes: experience.scenes,
          artDirection: CINEMATIC_DARK,
          motion: REDUCED_MOTION,
        }),
      );
      expect(html.length).toBeGreaterThan(0);
    });
  }

  it('covers all 11 primitives across the full fixture', () => {
    const experience = readFixture('full');
    const types = new Set(
      experience.scenes.flatMap((s) => s.blocks.map((b) => b.props.type)),
    );
    expect(types.size).toBe(11);
  });

  it('covers all 6 layouts across the full fixture', () => {
    const experience = readFixture('full');
    const layouts = new Set(experience.scenes.map((s) => s.layout));
    expect(layouts.size).toBe(6);
    for (const layout of LAYOUTS) expect(layouts.has(layout)).toBe(true);
  });

  it('every layout renders on its own with a single content block', () => {
    for (const layout of LAYOUTS) {
      const region =
        layout === 'grid'
          ? 'cells'
          : layout === 'split-left' || layout === 'split-right'
            ? 'left'
            : 'content';
      const scene = sceneSchema.parse({
        id: 's1',
        intent: 'hook',
        layout,
        blocks: [{ id: 'blk1', region, props: { type: 'eyebrow', text: 'Hi' } }],
      });
      const html = renderToStaticMarkup(
        SceneRenderer({
          scenes: [scene],
          artDirection: CINEMATIC_DARK,
          motion: CINEMATIC_MOTION,
        }),
      );
      expect(html).toContain('Hi');
    }
  });

  it('every Image in every fixture has a non-empty alt', () => {
    for (const name of FIXTURE_NAMES) {
      const experience = readFixture(name);
      const html = renderToStaticMarkup(
        SceneRenderer({
          scenes: experience.scenes,
          artDirection: CINEMATIC_DARK,
          motion: CINEMATIC_MOTION,
        }),
      );
      const imgTags = html.match(/<img[^>]*>/g) ?? [];
      for (const tag of imgTags) {
        expect(tag).toMatch(/alt="[^"]+"/);
      }
    }
  });

  it('never emits dangerouslySetInnerHTML outside the Slot path', () => {
    const experience = readFixture('full');
    const html = renderToStaticMarkup(
      SceneRenderer({
        scenes: experience.scenes,
        artDirection: CINEMATIC_DARK,
        motion: CINEMATIC_MOTION,
      }),
    );
    // The Slot iframe's `srcDoc` attribute is the one place raw HTML is
    // assembled by concatenation, by design — it's sandboxed, not escaped.
    // Nothing else in the output should contain an unescaped script tag from
    // any block's text content.
    const withoutSlotSrcdoc = html.replace(/srcdoc="[^"]*"/g, '');
    expect(withoutSlotSrcdoc).not.toContain('<script>');
  });

  it('renders an XSS payload in a text prop as escaped text, never as markup', () => {
    const scene = sceneSchema.parse({
      id: 's1',
      intent: 'hook',
      layout: 'centered',
      blocks: [{ id: 'b1', props: { type: 'body', text: '<script>alert(1)</script>' } }],
    });
    const html = renderToStaticMarkup(
      SceneRenderer({
        scenes: [scene],
        artDirection: CINEMATIC_DARK,
        motion: CINEMATIC_MOTION,
      }),
    );
    expect(html).not.toContain('<script>alert(1)</script>');
    expect(html).toContain('&lt;script&gt;');
  });
});

describe('isSafeHref', () => {
  it.each([
    'https://example.com',
    'http://example.com',
    'mailto:a@example.com',
    'tel:+15551234567',
    '#section',
    '/path',
  ])('accepts %s', (href) => {
    expect(isSafeHref(href)).toBe(true);
  });

  it.each([
    'javascript:alert(1)',
    'JAVASCRIPT:alert(1)',
    'data:text/html,<script>alert(1)</script>',
    'vbscript:msgbox(1)',
    '//evil.example',
  ])('rejects %s', (href) => {
    expect(isSafeHref(href)).toBe(false);
  });
});
