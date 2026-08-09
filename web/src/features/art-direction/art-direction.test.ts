import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, expectTypeOf, it } from 'vitest';

import type { BrandKit } from '@/schema';

import type { ArtDirection, TypeRoleKey } from './cinematic-dark';
import { CINEMATIC_DARK, FONT_REGISTRY, TYPE_SCALE } from './cinematic-dark';
import { contrastRatio } from './color';
import { CINEMATIC_MOTION, REDUCED_MOTION, staggerDelayMs } from './motion-vocabulary';
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
    expect(names.length).toBe(9 + 2 + 7 * 4 + 7 + 4 + 3);
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
    expect(FONT_REGISTRY.display.family).toBe('Fraunces');
    expect(FONT_REGISTRY.display.weights).toContain(500);
    expect(FONT_REGISTRY.display.weights).toContain(600);
  });

  it('every declared weight is actually used by some type role', () => {
    const used = new Set(Object.values(TYPE_SCALE).map((role) => role.weight));
    for (const weight of FONT_REGISTRY.display.weights) {
      expect(used.has(weight)).toBe(true);
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

  it('fails closed — a Result, not a best-effort guess — when lightening cannot help', () => {
    // Against cinematic-dark's near-black --bg, lightening toward white always
    // eventually clears 4.5:1 — that direction happens to be correct for this
    // art direction, which makes "cannot reach it" hard to trigger honestly
    // with the real token set. The genuine failure mode is a light --bg: the
    // algorithm only ever lightens, so a candidate converging on white against
    // a background that is already near-white can never separate from it,
    // however many attempts run. Synthesized here rather than skipped, because
    // rule 5 says to prove fail-closed by injection, not assume it.
    const lightBg: ArtDirection = {
      ...CINEMATIC_DARK,
      color: { ...CINEMATIC_DARK.color, bg: { r: 250, g: 250, b: 248, a: 1 } },
    };
    const result = resolveBrand(brandWith('#e8e8e0'), lightBg);
    expect(result.ok).toBe(false);
  });

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
