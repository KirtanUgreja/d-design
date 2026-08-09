import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, expectTypeOf, it } from 'vitest';

import type { BrandKit } from '@/schema';

import type { ArtDirection, TypeRoleKey } from './art-direction';
import { FONT_REGISTRY } from './art-direction';
import { CINEMATIC_DARK, TYPE_SCALE } from './cinematic-dark';
import { EDITORIAL_LIGHT } from './editorial-light';
import { contrastRatio, relativeLuminance } from './color';
import {
  CINEMATIC_MOTION,
  EDITORIAL_MOTION,
  REDUCED_MOTION,
  staggerDelayMs,
} from './motion-vocabulary';
import { ART_DIRECTION_IDS, resolveArtDirection } from './resolve-art-direction';
import { resolveBrand } from './resolve-brand';
import { fromCssVars, toCssVars } from './to-css-vars';

// ---------------------------------------------------------------------------
// Tokens
// ---------------------------------------------------------------------------

describe('token keys trace to the schema', () => {
  it('TYPE_SCALE has exactly the emphasis unions plus eyebrow/stat, no more, no fewer', () => {
    const expected: TypeRoleKey[] = [
      'hero',
      'section',
      'lead',
      'normal',
      'muted',
      'eyebrow',
      'stat',
    ];
    expect(Object.keys(TYPE_SCALE).sort()).toEqual([...expected].sort());
  });
});

describe('no token is typed as a bare string', () => {
  // Type-level, not runtime — the assignment below only compiles if every
  // leaf of ArtDirection is a literal, a number, or an object, never the
  // general `string` type. This is the test the phase file asks for: "walk
  // the token object's type." A future field typed as `color: string`
  // fails `tsc --noEmit`, which is part of the gate.
  type NoBareString<T> = T extends string
    ? string extends T
      ? never // the failure case: T is exactly `string`, not a literal
      : T
    : T extends readonly (infer U)[]
      ? readonly NoBareString<U>[]
      : T extends object
        ? { [K in keyof T]: NoBareString<T[K]> }
        : T;

  it('ArtDirection contains no bare-string leaf (compile-time)', () => {
    const assertion: NoBareString<ArtDirection> = CINEMATIC_DARK;
    expectTypeOf(assertion).toEqualTypeOf<NoBareString<ArtDirection>>();
  });
});

describe('to-css-vars round-trips', () => {
  it('emit -> parse -> the same color, type, rhythm, and texture', () => {
    const vars = toCssVars(CINEMATIC_DARK);
    const parsed = fromCssVars(vars);

    expect(parsed.color).toEqual(CINEMATIC_DARK.color);
    expect(parsed.rhythm).toEqual(CINEMATIC_DARK.rhythm);
    expect(parsed.texture).toEqual(CINEMATIC_DARK.texture);
    for (const role of Object.keys(CINEMATIC_DARK.type) as TypeRoleKey[]) {
      expect(parsed.type[role].size).toEqual(CINEMATIC_DARK.type[role].size);
      expect(parsed.type[role].leading).toBe(CINEMATIC_DARK.type[role].leading);
      expect(parsed.type[role].weight).toBe(CINEMATIC_DARK.type[role].weight);
    }
  });

  it('emits every value phase 02 extracted, and nothing that was not used', () => {
    const vars = toCssVars(CINEMATIC_DARK);
    const names = Object.keys(vars).sort();
    // 9 color + 2 font-family + 7*4 type-role + 7 space + 4 rhythm + 3 texture
    // + visual-blend + visual-strength
    expect(names.length).toBe(9 + 2 + 7 * 4 + 7 + 4 + 3 + 2);
    expect(vars['--space-1']).toBe('8px');
    expect(vars['--space-7']).toBe('160px');
    expect(vars['--measure']).toBe('62ch');
    expect(vars['--content-max']).toBe('1280px');
  });
});

describe('the two phase-02 corrections are the values that shipped', () => {
  it('--ink-faint is 50% alpha, not the drafted 38%', () => {
    expect(CINEMATIC_DARK.color.inkFaint.a).toBe(0.5);
  });

  it('the corrected ink-faint clears 4.5:1 against both surfaces', () => {
    const { inkFaint, bg, bgElevated } = CINEMATIC_DARK.color;
    expect(contrastRatio(inkFaint, bg, bg)).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio(inkFaint, bgElevated, bgElevated)).toBeGreaterThanOrEqual(4.5);
  });

  it('the display font is Fraunces (400/500/600), not the untested Instrument Serif', () => {
    expect(FONT_REGISTRY[CINEMATIC_DARK.fonts.display].family).toBe('Fraunces');
    expect(FONT_REGISTRY.fraunces.weights).toContain(500);
    expect(FONT_REGISTRY.fraunces.weights).toContain(600);
  });

  it('every weight some type role asks for is one the family actually ships', () => {
    // Inverted from "every declared weight is used": with four families in the
    // registry and two art directions, the interesting direction is the other
    // one — a role asking for a weight nobody downloaded renders as a synthetic
    // bold, which looks like a font-loading bug and is not one.
    for (const ad of [CINEMATIC_DARK, EDITORIAL_LIGHT]) {
      for (const role of Object.values(ad.type)) {
        const weights: readonly number[] = FONT_REGISTRY[ad.fonts[role.font]].weights;
        expect(weights).toContain(role.weight);
      }
    }
  });
});

// ---------------------------------------------------------------------------
// Brand resolver
// ---------------------------------------------------------------------------

describe('resolveBrand', () => {
  it('passes an already-compliant primary through unlightened', () => {
    const result = resolveBrand(brandWith('#f4b740'), CINEMATIC_DARK);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.accent).toEqual(result.value.accentRaw);
  });

  it('lightens a primary that fails 4.5:1 until it passes', () => {
    // A dark, low-contrast blue against near-black --bg.
    const result = resolveBrand(brandWith('#1a2b4c'), CINEMATIC_DARK);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(
      contrastRatio(
        result.value.accent,
        CINEMATIC_DARK.color.bg,
        CINEMATIC_DARK.color.bg,
      ),
    ).toBeGreaterThanOrEqual(4.5);
  });

  it('keeps the original, uncorrected color for non-text surfaces', () => {
    const result = resolveBrand(brandWith('#1a2b4c'), CINEMATIC_DARK);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.accentRaw).toEqual({ r: 0x1a, g: 0x2b, b: 0x4c, a: 1 });
    expect(result.value.accent).not.toEqual(result.value.accentRaw);
  });

  // This test used to assert the opposite, and it is worth saying why rather
  // than quietly rewriting it. It synthesized a light `--bg`, fed in a
  // near-white brand colour, and asserted `ok === false` — described as
  // "proving fail-closed by injection". What it was actually proving was a
  // bug: the resolver only ever lightened, so on a light ground it walked the
  // candidate *toward* the background and then reported the colour
  // unreachable. Every light art direction would have rejected usable brand
  // colours, and the test would have called that correct. `editorial-light`
  // is what turned the assertion from a guarantee into a symptom.
  it('darkens, rather than lightens, when the ground is light', () => {
    const result = resolveBrand(brandWith('#e8e8e0'), EDITORIAL_LIGHT);
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(
      contrastRatio(
        result.value.accent,
        EDITORIAL_LIGHT.color.bg,
        EDITORIAL_LIGHT.color.bg,
      ),
    ).toBeGreaterThanOrEqual(4.5);
    // Moved away from the ground, not toward it.
    expect(relativeLuminance(result.value.accent)).toBeLessThan(
      relativeLuminance(result.value.accentRaw),
    );
  });

  // With the direction chosen from the ground's own luminance, 4.5:1 is
  // reachable from *any* ground — no luminance exists where both black and
  // white fall short — so the `err` return is now unreachable for a
  // well-formed hex. It stays because rule 10 says anything that grants fails
  // closed, and the reachable failure is the one below.
  it('rejects a malformed hex rather than guessing at it', () => {
    const result = resolveBrand(brandWith('not-a-color'), CINEMATIC_DARK);
    expect(result.ok).toBe(false);
  });

  it('leaves --bg near-black regardless of the brand', () => {
    const pastel = resolveBrand(brandWith('#ffd6e8'), CINEMATIC_DARK);
    expect(pastel.ok).toBe(true);
    if (!pastel.ok) return;
    expect(pastel.value.bg).toEqual(CINEMATIC_DARK.color.bg);
  });
});

// Typed as `BrandKit` rather than inferred, so the font fields are checked
// against the registry ids the schema actually allows. They used to read
// `'Fraunces'`/`'Inter'` — family *names*, which the Pydantic `FontId` Literal
// (phase 10) no longer has a representation for. A user-supplied family string
// is the most natural-looking free-text token in the system and the one that
// most easily carries a payload, so the fix is the schema and this is the fix
// landing.
function brandWith(primary: string): BrandKit {
  return {
    id: 'brand-1',
    displayFont: 'fraunces',
    textFont: 'inter',
    primary,
    secondary: '#ffffff',
    neutral: '#888888',
    logoAssetId: null,
  };
}

// ---------------------------------------------------------------------------
// Motion
// ---------------------------------------------------------------------------

describe('REDUCED_MOTION', () => {
  it('is opacity-only, 200ms or less, no transform, for every intent that moves', () => {
    for (const intent of ['reveal', 'emphasize', 'parallax'] as const) {
      const def = REDUCED_MOTION.intents[intent];
      expect(def.durationMs).toBeLessThanOrEqual(200);
      expect(def.distancePx).toBe(0);
      expect(def.scale).toBe(1);
    }
  });

  it('none stays instant in both vocabularies', () => {
    expect(CINEMATIC_MOTION.intents.none.durationMs).toBe(0);
    expect(REDUCED_MOTION.intents.none.durationMs).toBe(0);
  });
});

describe('staggerDelayMs', () => {
  it('caps at 5 siblings', () => {
    const atCap = staggerDelayMs(CINEMATIC_MOTION, 5);
    expect(staggerDelayMs(CINEMATIC_MOTION, 6)).toBe(atCap);
    expect(staggerDelayMs(CINEMATIC_MOTION, 100)).toBe(atCap);
  });

  it('is linear in index below the cap', () => {
    expect(staggerDelayMs(CINEMATIC_MOTION, 2)).toBe(CINEMATIC_MOTION.staggerMs * 2);
  });
});

describe('the motion vocabulary is data', () => {
  it('has no typeof window, no process.env, no media-query read', () => {
    // Strip comments first — this file's own doc comments explain the rule
    // by naming the forbidden constructs, which would otherwise trip the
    // check on prose rather than code.
    const source = readFileSync(join(import.meta.dirname, 'motion-vocabulary.ts'), 'utf8')
      .replace(/\/\/.*$/gm, '')
      .replace(/\/\*[\s\S]*?\*\//g, '');
    expect(source).not.toMatch(/typeof window/);
    expect(source).not.toMatch(/process\.env/);
    expect(source).not.toMatch(/matchMedia/);
  });
});

// ---------------------------------------------------------------------------
// Art direction #2 — docs/v1/spec.md Risk 4
//
// "The art-direction layer is unproven until there are two." These are the
// assertions that make the second one a claim rather than a second file: that
// it is genuinely a different design, that it is as accessible as the first,
// and that the layer is total — every art direction answers every token, or
// the renderer falls back to a browser default and nobody notices until a
// customer does.
// ---------------------------------------------------------------------------

describe('editorial-light', () => {
  const BOTH = [CINEMATIC_DARK, EDITORIAL_LIGHT];

  it('emits exactly the same variable names as cinematic-dark', () => {
    // Totality. A missing `--type-lead-size` does not throw anywhere — the
    // block asks for `var(--type-lead-size)`, gets nothing, and inherits.
    expect(Object.keys(toCssVars(EDITORIAL_LIGHT)).sort()).toEqual(
      Object.keys(toCssVars(CINEMATIC_DARK)).sort(),
    );
  });

  it('round-trips through the CSS-variable format like any other direction', () => {
    const parsed = fromCssVars(toCssVars(EDITORIAL_LIGHT));
    expect(parsed.color).toEqual(EDITORIAL_LIGHT.color);
    expect(parsed.rhythm).toEqual(EDITORIAL_LIGHT.rhythm);
    expect(parsed.texture).toEqual(EDITORIAL_LIGHT.texture);
  });

  it('is a light ground with dark ink — the inverse of #1, not a tint of it', () => {
    expect(relativeLuminance(EDITORIAL_LIGHT.color.bg)).toBeGreaterThan(0.8);
    expect(relativeLuminance(CINEMATIC_DARK.color.bg)).toBeLessThan(0.05);
    expect(relativeLuminance(EDITORIAL_LIGHT.color.ink)).toBeLessThan(0.05);
  });

  it('shares no font family with cinematic-dark', () => {
    const families = (ad: ArtDirection) =>
      new Set([
        FONT_REGISTRY[ad.fonts.display].family,
        FONT_REGISTRY[ad.fonts.text].family,
      ]);
    const a = families(CINEMATIC_DARK);
    for (const family of families(EDITORIAL_LIGHT)) {
      expect(a.has(family)).toBe(false);
    }
  });

  it('is a materially different design, not the same numbers relit', () => {
    // Every group, because "unrecognizably different output" is the claim and
    // a palette swap alone would not earn it. Not a threshold on how different
    // — that would be a taste assertion — just that no group is copied.
    expect(EDITORIAL_LIGHT.type).not.toEqual(CINEMATIC_DARK.type);
    expect(EDITORIAL_LIGHT.rhythm).not.toEqual(CINEMATIC_DARK.rhythm);
    expect(EDITORIAL_LIGHT.texture).not.toEqual(CINEMATIC_DARK.texture);
    expect(EDITORIAL_MOTION).not.toEqual(CINEMATIC_MOTION);
  });

  it('every text role clears 4.5:1 against its own ground, in both directions', () => {
    // The accessibility floor is a property of the layer, not of art direction
    // #1. A second direction that ships an unreadable eyebrow is a second
    // direction that should not ship.
    for (const ad of BOTH) {
      for (const [name, role] of Object.entries(ad.type)) {
        const ink = role.color ? ad.color[role.color] : ad.color.ink;
        const ratio = contrastRatio(ink, ad.color.bg, ad.color.bg);
        expect(
          ratio,
          `${ad.id}: ${name} is ${ratio.toFixed(2)}:1 against --bg`,
        ).toBeGreaterThanOrEqual(4.5);
      }
    }
  });

  it('motion arrives rather than drifts — every intent shorter than #1s', () => {
    for (const intent of ['reveal', 'emphasize'] as const) {
      expect(EDITORIAL_MOTION.intents[intent].durationMs).toBeLessThan(
        CINEMATIC_MOTION.intents[intent].durationMs,
      );
    }
    expect(EDITORIAL_MOTION.staggerMs).toBeLessThan(CINEMATIC_MOTION.staggerMs);
  });
});

describe('resolveArtDirection', () => {
  it('answers for every id the schema allows', () => {
    for (const id of ART_DIRECTION_IDS) {
      const resolved = resolveArtDirection(id);
      expect(resolved.artDirection.id).toBe(id);
      expect(resolved.motion.intents.reveal.durationMs).toBeGreaterThan(0);
    }
  });

  it('pairs each direction with its own motion, not a shared default', () => {
    expect(resolveArtDirection('cinematic-dark').motion).toBe(CINEMATIC_MOTION);
    expect(resolveArtDirection('editorial-light').motion).toBe(EDITORIAL_MOTION);
  });
});
