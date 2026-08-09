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

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { CINEMATIC_MOTION, REDUCED_MOTION } from '@/features/art-direction';
import { seededArtDirection } from '@/features/art-direction/server';
import { experienceSchema, sceneSchema } from '@/schema';

import { AbstractVisualBlock } from './blocks/abstract-visual';
import { isSafeHref } from './blocks/href-safety';
import { seedFromId } from './blocks/visual-seed';
import { SceneRenderer } from './scene-renderer';

// Resolved from the seeded record rather than imported as a constant — as of
// v2 phase 01 there is no constant, and this is what a page actually renders
// with. The renderer takes an `ArtDirection` object either way, which is the
// point: the token layer moved and the renderer took no change.
const CINEMATIC_DARK = seededArtDirection('cinematic-dark').artDirection;

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

// --- AbstractVisual: five generators, deterministic from a scene id --------

describe('seedFromId', () => {
  // The same table as `api/tests/test_visual_seed.py`. Two implementations of
  // one hash — the server derives a seed during a build, the editor derives
  // one for reroll, and the alternative to a second implementation is a
  // network round trip for a number. Shared fixtures are what make the
  // duplication survivable: change one side without the other and this turns
  // red.
  //
  // The non-ASCII rows are the ones that matter. Python hashes UTF-8 bytes and
  // the obvious TypeScript loop walks UTF-16 code units masked to a byte; the
  // two agree on ASCII and diverge on everything else, which is exactly the
  // bug these caught.
  const FIXTURES: Record<string, number> = {
    'scene-1': 860226354,
    'scene-1-hook': 342120084,
    s1: 139573449,
    '': 18652614,
    'a-much-longer-scene-identifier-than-usual': 1412726095,
    '🎬': 1406619490,
    'scène-é': 1341928168,
  };

  it('matches the Python implementation byte for byte', () => {
    for (const [id, expected] of Object.entries(FIXTURES)) {
      expect(seedFromId(id), id).toBe(expected);
    }
  });

  it('always lands inside the schema’s seed range', () => {
    for (const id of [...Object.keys(FIXTURES), 'x'.repeat(200)]) {
      expect(seedFromId(id)).toBeGreaterThanOrEqual(0);
      expect(seedFromId(id)).toBeLessThanOrEqual(2147483647);
    }
  });
});

describe('the six AbstractVisual generators', () => {
  const GENERATORS = [
    'halftone-field',
    'particle-field',
    'grid-lines',
    'hatch-drift',
    'dither-fade',
    'block-collage',
  ] as const;
  const INTENSITIES = ['subtle', 'medium', 'bold'] as const;

  function visual(generator: string, intensity: string, seed = 42) {
    return renderToStaticMarkup(
      createElement(AbstractVisualBlock, {
        props: { type: 'abstract-visual', generator, intensity, seed },
      } as never),
    );
  }

  // The ban, asserted against rendered output rather than against source. A
  // generator could import a clean pattern and still compose a ramp out of it;
  // this is what says it did not. docs/v2/plan/14-texture-without-gradient.md.
  it('emits no gradient and no blur, at any intensity', () => {
    for (const generator of GENERATORS) {
      for (const intensity of INTENSITIES) {
        const html = visual(generator, intensity);
        expect(html, `${generator}/${intensity}`).not.toMatch(/gradient\(/);
        expect(html, `${generator}/${intensity}`).not.toMatch(/blur\(/);
        expect(html, `${generator}/${intensity}`).not.toMatch(/box-shadow|text-shadow/);
      }
    }
  });

  // Colour reaches a generator as `var(--accent)`, never as a resolved value.
  // v1 called `toCssColor(palette.accent)` in this layer, which is a token
  // becoming a string outside the one file allowed to do it.
  it('paints only token references, never a resolved colour', () => {
    for (const generator of GENERATORS) {
      const html = visual(generator, 'bold');
      expect(html, generator).not.toMatch(/rgb\(/);
      expect(html, generator).not.toMatch(/#[0-9a-fA-F]{3,8}/);
    }
  });

  it('all six render at all three intensities', () => {
    for (const generator of GENERATORS) {
      for (const intensity of INTENSITIES) {
        const html = visual(generator, intensity);
        expect(html.length, `${generator}/${intensity}`).toBeGreaterThan(50);
        expect(html).toContain('aria-hidden');
      }
    }
  });

  it('the same seed gives byte-identical output', () => {
    // Determinism across processes and across a restart is the whole promise:
    // the published page and the edited page have to be the same page, and a
    // visual that re-randomizes on render would break that quietly.
    for (const generator of GENERATORS) {
      expect(visual(generator, 'medium', 7)).toBe(visual(generator, 'medium', 7));
    }
  });

  it('a different seed gives different output', () => {
    for (const generator of GENERATORS) {
      expect(visual(generator, 'medium', 7), generator).not.toBe(
        visual(generator, 'medium', 8),
      );
    }
  });

  // Not asserted here: `assertNoPresentationalValues`. That walker lives in
  // `api/schema/no_style.py` and has no TypeScript twin on purpose — a second
  // copy of a rule is the drift the codegen arrangement exists to prevent. The
  // generator-carries-no-values assertion is in
  // `api/features/generation/test_checks.py`, where the walker is.
});
