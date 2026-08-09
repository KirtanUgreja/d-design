import { readFileSync } from 'node:fs';
import { join } from 'node:path';

import { describe, expect, expectTypeOf, it } from 'vitest';

import type { BrandKit } from '@/schema';

import type { ArtDirection, Texture, TypeRoleKey } from './art-direction';
import { FONT_REGISTRY, LAYOUTS, px } from './art-direction';
import { contrastRatio, relativeLuminance, toCssColor } from './color';
import { fromRecord } from './from-record';
import { staggerDelayMs } from './motion-vocabulary';
import { resolveBrand } from './resolve-brand';
import { fromMotionRecord } from './from-motion-record';
import {
  seededMotionRecord,
  seededMotionRecords,
  seededRecord,
  seededRecords,
} from './seeded-records';
import { brandCssVars, fromCssVars, toCssVars } from './to-css-vars';

// The two art directions, resolved from the seeded records rather than
// imported as constants — because as of v2 phase 01 there are no constants.
// `seededRecords()` reads the checked-in fixture that
// `api/features/art_direction/seed.py` generates and migration 0011 seeds the
// database from, so what these tests assert about is what a page renders with.
function resolved(id: string): ArtDirection {
  const result = fromRecord(seededRecord(id));
  if (!result.ok) throw new Error(`${id}: ${result.error.message}`);
  return result.value.artDirection;
}

// Same directory the schema fixtures live in, reached the same way
// `src/schema/schema.test.ts` reaches them.
const FIXTURES = join(
  import.meta.dirname,
  '..',
  '..',
  '..',
  '..',
  'api',
  'schema',
  'fixtures',
);

const CINEMATIC_DARK = resolved('cinematic-dark');
const EDITORIAL_LIGHT = resolved('editorial-light');
const TYPE_SCALE = CINEMATIC_DARK.type;

// The vocabularies, resolved from their seeded records — as of v2 phase 02
// there are no constants for these either, and no art direction hands one out.
const CINEMATIC_MOTION = fromMotionRecord(seededMotionRecord('cinematic-slow')).full;
const EDITORIAL_MOTION = fromMotionRecord(
  seededMotionRecord('editorial-restrained'),
).full;
const REDUCED_MOTION = fromMotionRecord(seededMotionRecord('cinematic-slow')).reduced;

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

  // Every token group, and `id` is deliberately not one of them. It was a
  // two-value literal union until v2 phase 01 and is now a `string`, because
  // art directions are rows and a union cannot enumerate rows — but an id is a
  // name, not a token: nothing reads it to decide how anything looks, and
  // `to-css-vars.ts` never emits it. Excluding it here rather than weakening
  // the check is what keeps the test saying what it says.
  type Tokens = Omit<ArtDirection, 'id'>;

  it('ArtDirection contains no bare-string leaf, id aside (compile-time)', () => {
    const { id: _id, ...tokens } = CINEMATIC_DARK;
    const assertion: NoBareString<Tokens> = tokens;
    expectTypeOf(assertion).toEqualTypeOf<NoBareString<Tokens>>();
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
    // 9 color + 2 font-family + 7*4 type-role + 7 space + 4 rhythm
    // + visual-blend + visual-strength + 9 fit (1 min-block + 6 per-layout
    // + place + scroll-margin) + texture: 1 count + 3 layers, each 5 common
    // fields (kind, opacity, color, scale, offset) plus its own — halftone
    // angle+steps, dither steps, grain density + image: edge, veil, and this
    // direction's grain overlay as a 7th texture layer (5 common + density).
    expect(names.length).toBe(
      9 + 2 + 7 * 4 + 7 + 4 + 2 + 9 + (1 + 3 * 5 + 2 + 1 + 1) + (2 + 5 + 1),
    );
    expect(vars['--space-1']).toBe('8px');
    expect(vars['--space-7']).toBe('160px');
    expect(vars['--measure']).toBe('62ch');
    expect(vars['--content-max']).toBe('1280px');
  });
});

describe('texture carries colour by pattern, never by ramp', () => {
  // Every kind, including the two no shipped direction uses yet. A vocabulary
  // whose unused half has never been round-tripped is a vocabulary with two
  // members that work and four that compile.
  const ALL_KINDS: Texture = [
    {
      kind: 'grain',
      intensity: 0.05,
      color: 'ink',
      scale: px(64),
      offset: px(0),
      density: 2,
    },
    {
      kind: 'halftone',
      intensity: 0.5,
      color: 'accentSoft',
      scale: px(11),
      offset: px(0),
      angle: 15,
      steps: 3,
    },
    {
      kind: 'hatch',
      intensity: 0.3,
      color: 'ink',
      scale: px(8),
      offset: px(0),
      angle: 45,
      cross: true,
      density: 2,
    },
    {
      kind: 'dither',
      intensity: 0.8,
      color: 'bg',
      scale: px(3),
      offset: px(0),
      steps: 4,
    },
    {
      kind: 'weave',
      intensity: 0.1,
      color: 'ink',
      scale: px(7),
      offset: px(0),
      density: 3,
    },
    {
      kind: 'rule',
      intensity: 0.14,
      color: 'ink',
      scale: px(32),
      // Riso misregistration: the same kind, a second colour, nudged. It falls
      // out of the layer list rather than needing a mechanism, which is the
      // sign the layer list is the right shape.
      offset: px(2),
      axis: 'inline',
      weight: 'thick',
    },
  ];

  const withTexture = (texture: Texture): ArtDirection => ({
    ...CINEMATIC_DARK,
    texture,
  });

  it('round-trips all six kinds with their own fields', () => {
    const parsed = fromCssVars(toCssVars(withTexture(ALL_KINDS)));
    expect(parsed.texture).toEqual(ALL_KINDS);
  });

  it('round-trips two layers of the same kind, which is what riso needs', () => {
    const riso: Texture = [
      {
        kind: 'weave',
        intensity: 0.2,
        color: 'accent',
        scale: px(7),
        offset: px(0),
        density: 2,
      },
      {
        kind: 'weave',
        intensity: 0.2,
        color: 'ink',
        scale: px(7),
        offset: px(2),
        density: 2,
      },
    ];
    const parsed = fromCssVars(toCssVars(withTexture(riso)));
    // Indexed emission, not keyed by kind — keyed would collapse these to one.
    expect(parsed.texture).toEqual(riso);
  });

  it('rejects a texture kind the union no longer has', () => {
    const vars = { ...toCssVars(CINEMATIC_DARK), '--texture-0-kind': 'glow' };
    // `glow` and `vignette` were removed rather than deprecated. Parsing that
    // tolerated an unknown kind is how a removed kind survives in stored data
    // and quietly comes back.
    expect(() => fromCssVars(vars)).toThrow(/not a texture kind/);
  });

  it('emits no gradient function in any token value', () => {
    for (const ad of [CINEMATIC_DARK, EDITORIAL_LIGHT, withTexture(ALL_KINDS)]) {
      for (const [name, value] of Object.entries(toCssVars(ad))) {
        expect(value, `${name} carries a gradient`).not.toMatch(/gradient\(/);
      }
    }
  });
});

describe('scene fit is the art direction answering, not the renderer deciding', () => {
  it('resolves one variable per layout, so the renderer looks up rather than branches', () => {
    const vars = toCssVars(CINEMATIC_DARK);
    // Every layout, always emitted — a missing name would make the renderer's
    // `var()` fall back to nothing and silently drop the floor.
    for (const layout of LAYOUTS) {
      expect(vars[`--scene-min-block-${layout}`]).toBeDefined();
    }
  });

  it('cinematic-dark gives every layout the frame', () => {
    const vars = toCssVars(CINEMATIC_DARK);
    expect(vars['--scene-fit-min-block']).toBe('100svh');
    for (const layout of LAYOUTS) {
      expect(vars[`--scene-min-block-${layout}`]).toBe('var(--scene-fit-min-block)');
    }
    expect(vars['--scene-place']).toBe('center');
  });

  // The whole claim of this phase, as an assertion: two art directions give
  // different answers about a scene's frame, and there is no second code path
  // for the renderer to take. If this test and the one above both pass, `fit`
  // is a token. `renderer/` is grepped for the units in the test below.
  it('editorial-light lets document-shaped layouts run at content height', () => {
    const vars = toCssVars(EDITORIAL_LIGHT);
    expect(vars['--scene-min-block-stack']).toBe('auto');
    expect(vars['--scene-min-block-grid']).toBe('auto');
    expect(vars['--scene-min-block-full-bleed']).toBe('var(--scene-fit-min-block)');
    expect(vars['--scene-min-block-centered']).toBe('var(--scene-fit-min-block)');
    expect(vars['--scene-place']).toBe('start');
  });

  it('round-trips a fit table in which some layouts are content-height', () => {
    // The lossy shape this guards against: reconstructing `fitMinBlock` by
    // reading a per-layout value back. An art direction whose layouts all
    // answered `content` would have nothing to read it from, so the length is
    // emitted once in its own variable and the per-layout names point at it.
    const parsed = fromCssVars(toCssVars(EDITORIAL_LIGHT));
    expect(parsed.rhythm.fit).toEqual(EDITORIAL_LIGHT.rhythm.fit);
    expect(parsed.rhythm.fitMinBlock).toEqual(EDITORIAL_LIGHT.rhythm.fitMinBlock);
    expect(parsed.rhythm.fitPlace).toBe('start');
  });

  it('rejects a placement value the type does not have, rather than widening', () => {
    const vars = { ...toCssVars(CINEMATIC_DARK), '--scene-place': 'middle' };
    expect(() => fromCssVars(vars)).toThrow(/not a scene place/);
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

  it('has no way to change the ground, whatever the brand', () => {
    // "Brand colours map into semantic roles, they do not replace them"
    // asserted structurally rather than by comparison: `resolveBrand` returns
    // an accent and the accent it was given, and there is no `bg` on the type
    // for a brand to reach. It used to return the whole palette with one field
    // swapped, which made this a value assertion — and hid a real bug, since
    // `accentSoft` came back as the art direction's own hue.
    const pastel = resolveBrand(brandWith('#ffd6e8'), CINEMATIC_DARK);
    expect(pastel.ok).toBe(true);
    if (!pastel.ok) return;
    expect(Object.keys(pastel.value).sort()).toEqual(['accent', 'accentRaw']);
  });
});

describe('the brand overlay derives in CSS, not in JavaScript', () => {
  // The point of the whole arrangement: one variable is overridden and every
  // token that depends on it follows, with no JS pass — which is what phase 07
  // needs inside a View Transition.
  it('writes accent-soft as a mix of var(--accent), not as a computed colour', () => {
    const resolved = resolveBrand(brandWith('#1a2b4c'), CINEMATIC_DARK);
    expect(resolved.ok).toBe(true);
    if (!resolved.ok) return;

    const vars = brandCssVars(CINEMATIC_DARK, resolved.value.accent);
    expect(vars['--accent']).toBe(toCssColor(resolved.value.accent));
    expect(vars['--accent-soft']).toContain('var(--accent)');
    expect(vars['--accent-soft']).toContain('in oklch');
  });

  it('takes the mix ratio from the art direction, never from the emitter', () => {
    // 12% on cinematic-dark, 10% on editorial-light — the alpha each direction
    // already declared on its own `accentSoft` token. They mean different
    // things (a glow, versus a wash behind a pull quote), so a constant here
    // would be this file overruling the token layer.
    const accent = CINEMATIC_DARK.color.accent;
    expect(brandCssVars(CINEMATIC_DARK, accent)['--accent-soft']).toContain('12%');
    expect(brandCssVars(EDITORIAL_LIGHT, accent)['--accent-soft']).toContain('10%');
  });

  it('overrides only the two variables a brand owns', () => {
    // A brand maps into semantic roles; it does not get to restyle the page.
    // An overlay that grew a third key would be a brand reaching past its role,
    // and this is the assertion that notices.
    const keys = Object.keys(brandCssVars(CINEMATIC_DARK, CINEMATIC_DARK.color.accent));
    expect(keys.sort()).toEqual(['--accent', '--accent-soft']);
  });

  it("leaves the art direction's own emission untouched", () => {
    // The overlay is a separate map applied on top, so an experience with no
    // brand renders exactly what it rendered before — which is what keeps the
    // byte-identical proof above meaningful.
    expect(toCssVars(CINEMATIC_DARK)['--accent-soft']).toBe('rgb(244 183 64 / 12%)');
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

describe('reduced motion is a floor, and every vocabulary has one', () => {
  // Per-vocabulary since v2 phase 02, where it was one global constant before.
  // The check has to run over all of them now, which is the point: a fifth
  // vocabulary that shipped a reduced mode with travel in it is exactly what
  // this catches, and a single-constant test could not have.
  it('is opacity-only, no transform, no parallax, for every vocabulary', () => {
    for (const record of seededMotionRecords()) {
      const { reduced } = fromMotionRecord(record);
      for (const intent of ['reveal', 'emphasize', 'parallax'] as const) {
        const def = reduced.intents[intent];
        expect(def.durationMs, `${record.id}/${intent}`).toBeLessThanOrEqual(300);
        expect(def.distancePx, `${record.id}/${intent}`).toBe(0);
        expect(def.scale, `${record.id}/${intent}`).toBe(1);
      }
      // A sequence is a movement, and the floor has none.
      expect(reduced.staggerMs, record.id).toBe(0);
    }
  });

  it('never turns `none` into something that animates', () => {
    // `none` means the author said this does not move, and reduced motion is
    // not an instruction to start.
    for (const record of seededMotionRecords()) {
      const { full, reduced } = fromMotionRecord(record);
      expect(full.intents.none.durationMs, record.id).toBe(0);
      expect(reduced.intents.none.durationMs, record.id).toBe(0);
    }
  });
});

describe('staggerDelayMs', () => {
  it("caps at the vocabulary's own cap", () => {
    const cap = CINEMATIC_MOTION.staggerCap;
    const atCap = staggerDelayMs(CINEMATIC_MOTION, cap);
    expect(staggerDelayMs(CINEMATIC_MOTION, cap + 1)).toBe(atCap);
    expect(staggerDelayMs(CINEMATIC_MOTION, 100)).toBe(atCap);
  });

  it('still caps at 5 siblings, which is what both vocabularies declare', () => {
    // A module constant in v1 and a field now. The value did not change, and
    // this is the assertion that would have noticed if it had.
    for (const record of seededMotionRecords()) {
      expect(record.staggerCap, record.id).toBe(5);
    }
  });

  it('is linear in index below the cap', () => {
    expect(staggerDelayMs(CINEMATIC_MOTION, 2)).toBe(CINEMATIC_MOTION.staggerMs * 2);
  });
});

describe('the v2 vocabularies are what v1 authored', () => {
  // The same claim, and the same shape of proof, as the art directions above:
  // the objects v1's constants held, captured as they were deleted. A rename
  // that also retuned the motion would be two changes wearing one commit
  // message, and this is what makes that impossible to do by accident.
  const V1_MOTION = JSON.parse(
    readFileSync(join(FIXTURES, 'motion_v1.json'), 'utf8'),
  ) as Record<string, unknown>;

  it.each([
    ['cinematic-slow', CINEMATIC_MOTION],
    ['editorial-restrained', EDITORIAL_MOTION],
  ])('%s is byte-identical to its v1 constant', (id, vocabulary) => {
    // `staggerCap` was a module constant in v1 and is a field now, so it is not
    // in the captured object — compared against 5 separately, above.
    const { staggerCap: _cap, ...rest } = vocabulary;
    expect(rest).toEqual(V1_MOTION[id]);
  });

  it("reduced motion keeps v1 timing and gains the vocabulary's own curve", () => {
    // The one deliberate difference. v1 had a single global REDUCED_MOTION that
    // both vocabularies borrowed, easing on cinematic's curve; each declares its
    // own duration now — unchanged at 200ms — and fades on its own easing at
    // its own trigger, because those are properties of the vocabulary rather
    // than of the floor.
    const v1Reduced = V1_MOTION.reduced as {
      intents: { reveal: { durationMs: number } };
    };
    const editorialReduced = fromMotionRecord(
      seededMotionRecord('editorial-restrained'),
    ).reduced;

    expect(editorialReduced.intents.reveal.durationMs).toBe(
      v1Reduced.intents.reveal.durationMs,
    );
    expect(editorialReduced.intents.reveal.ease).toEqual(
      EDITORIAL_MOTION.intents.reveal.ease,
    );
    expect(editorialReduced.intents.reveal.ease).not.toEqual(
      REDUCED_MOTION.intents.reveal.ease,
    );
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

  it('emits exactly the same variable names as cinematic-dark, texture aside', () => {
    // Totality. A missing `--type-lead-size` does not throw anywhere — the
    // block asks for `var(--type-lead-size)`, gets nothing, and inherits.
    //
    // `--texture-*` is exempt from phase 14, and the exemption is structural
    // rather than a concession. Every other variable is read unconditionally,
    // so a direction that omits one is a direction with a hole. A texture
    // variable is read only inside the branch for that layer's *kind* — a
    // `weave` layer never asks for an angle — and the emitter switches on the
    // same discriminant the renderer does. Requiring name-set equality here
    // would force every direction to emit every field of every kind it does
    // not use.
    //
    // What replaces it is stronger, not weaker: the round trip below reads
    // back exactly the fields the kind declares and throws on a missing one,
    // and the all-six-kinds test asserts it for kinds no shipped direction
    // uses yet.
    const withoutTexture = (ad: ArtDirection) =>
      Object.keys(toCssVars(ad))
        .filter((name) => !name.startsWith('--texture-'))
        .sort();
    expect(withoutTexture(EDITORIAL_LIGHT)).toEqual(withoutTexture(CINEMATIC_DARK));
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

// ---------------------------------------------------------------------------
// The v2 format, and the migration's only real assertion.
//
// "A format migration that changes a pixel has changed a design."
// docs/v2/plan/01-ad-format.md -> Verify.
// ---------------------------------------------------------------------------

describe('the v2 record renders what the v1 constants rendered', () => {
  // The CSS-variable maps the deleted `cinematic-dark.ts` and
  // `editorial-light.ts` emitted, captured at the moment they were deleted.
  //
  // A snapshot rather than a live comparison, because the thing being compared
  // against no longer exists — and that is the honest durable form of the
  // claim. The alternative was keeping the constants around solely to be
  // compared against, which is two sources of truth kept alive by a test.
  const V1_CSS = JSON.parse(
    readFileSync(join(FIXTURES, 'art_direction_css_v1.json'), 'utf8'),
  ) as Record<string, Record<string, string>>;

  for (const id of ['cinematic-dark', 'editorial-light']) {
    it(`${id} emits byte-identical custom properties`, () => {
      expect(toCssVars(resolved(id))).toEqual(V1_CSS[id]);
    });
  }
});

describe('fromRecord', () => {
  it('resolves every seeded record', () => {
    const byId = new Map(
      seededRecords().map((record) => {
        const result = fromRecord(record);
        if (!result.ok) throw new Error(`${record.id}: ${result.error.message}`);
        return [record.id, result.value];
      }),
    );
    for (const [id, resolvedRecord] of byId) {
      expect(resolvedRecord.artDirection.id).toBe(id);
    }
  });

  it('hands back no motion at all — that is the axis, and it is separate', () => {
    // v1's `resolveArtDirection` returned `{artDirection, motion}`, which is a
    // code table by another name: an art direction that comes with its motion
    // is one you cannot pick motion independently of. `defaultMotion` survives
    // as what a *new* experience inherits, and nothing resolves it at render
    // time.
    const resolvedRecord = fromRecord(seededRecord('cinematic-dark'));
    expect(resolvedRecord.ok).toBe(true);
    if (!resolvedRecord.ok) return;
    expect(Object.keys(resolvedRecord.value).sort()).toEqual(['artDirection', 'record']);
  });

  it('every art direction names a motion vocabulary that exists', () => {
    // The default is a string crossing a table boundary with no foreign key
    // behind it — `default_motion` is text, and `motion_vocabularies` is a
    // different table. This is what stands in for the constraint, and it is
    // what would have caught the ids being renamed in one place and not the
    // other.
    const known = new Set(seededMotionRecords().map((record) => record.id));
    for (const record of seededRecords()) {
      expect(known, record.id).toContain(record.extensions.defaultMotion);
    }
  });

  it('fails closed on a font family the registry does not have', () => {
    // The control that keeps a free-text font family out of a stylesheet. A
    // fallback here would publish a page in the wrong typeface and report
    // success; a pass-through would be a CSS injection with a friendly label.
    const record = seededRecord('cinematic-dark');
    const forged = {
      ...record,
      tokens: {
        ...record.tokens,
        font: {
          ...record.tokens.font,
          display: { ...record.tokens.font.display, $value: 'Comic Sans MS' },
        },
      },
    };
    const result = fromRecord(forged);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('invalid_input');
  });

  it('does not carry the optional hex fallback into the resolved colour', () => {
    // `components` is authoritative and `hex` is the spec's optional fallback.
    // Re-parsing the fallback would make a lossy serialization the source of a
    // number the contrast maths depends on, so this proves the components are
    // what is read: a record whose hex disagrees with its components resolves
    // to the components.
    const record = seededRecord('cinematic-dark');
    const lying = {
      ...record,
      tokens: {
        ...record.tokens,
        color: {
          ...record.tokens.color,
          bg: {
            ...record.tokens.color.bg,
            $value: { ...record.tokens.color.bg.$value, hex: '#ffffff' },
          },
        },
      },
    };
    const result = fromRecord(lying);
    expect(result.ok).toBe(true);
    if (result.ok)
      expect(result.value.artDirection.color.bg).toEqual(CINEMATIC_DARK.color.bg);
  });
});
