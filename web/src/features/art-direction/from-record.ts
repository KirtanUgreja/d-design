// The stored record -> the `ArtDirection` the renderer reads.
//
// The seam that replaced two TypeScript constants. `cinematic-dark.ts` and
// `editorial-light.ts` used to hold these values; the values now live in
// `art_directions`, seeded by migration 0011 from `api/features/art_direction/
// seed.py`, and this is the one place a row becomes tokens.
//
// **It is a total mapping between two declared shapes, not a cast.**
// `ArtDirectionRecord` is generated from Pydantic and `ArtDirection` is
// hand-written here, so a field added on either side is a compile error rather
// than a silently missing token. That property is the whole reason the record's
// fluid layer is typed in Python instead of stored as an opaque blob — an
// opaque blob would have made this file a pile of unchecked assertions sitting
// between the database and every published page.
//
// **Two things fail closed rather than falling back**, and both are the same
// kind of failure: a value that arrived from storage naming something this
// process does not have.
//
//   * a font family that is not in `FONT_REGISTRY`. A family name that fell
//     back to a system font would publish a page in the wrong typeface and
//     report success; a family name that fell through *as a string* would be a
//     free-text font family reaching a stylesheet, which docs/v1/plan/
//     10-brand-and-uploads.md calls the most natural-looking free-text token in
//     the system and the one that most easily carries a payload.
//   * a motion vocabulary id that names no vocabulary.
//
// Nothing here reads the environment, and nothing here is async. It runs in the
// three processes the renderer runs in and behaves identically in all of them
// (rule 6).

import type { ArtDirectionRecord } from '@/schema';
import { err, ok, type Result } from '@/lib/result';

import type {
  ArtDirection,
  ClampTriple,
  FontFamilyId,
  FontSlot,
  ImageTreatment,
  Length,
  Palette,
  Rhythm,
  Texture,
  TypeRole,
  TypeRoleKey,
} from './art-direction';
import { FONT_REGISTRY } from './art-direction';
import type { Color } from './color';
import { CINEMATIC_MOTION, EDITORIAL_MOTION, REDUCED_MOTION } from './motion-vocabulary';
import type { MotionVocabulary } from './motion-vocabulary';

// DTCG carries colour channels in 0-1; `Color` is 8-bit because that is what
// `rgb()` takes and what the WCAG maths in `color.ts` was written against. The
// same constant is `_CHANNEL_MAX` in `api/features/art_direction/dtcg.py` — an
// 8-bit assumption spelled as a bare 255 in two languages is exactly the kind
// of agreement that drifts unnoticed, so both are named.
const CHANNEL_MAX = 255;

type Record_ = ArtDirectionRecord;
type Tokens = Record_['tokens'];
type Fluid = Record_['extensions']['fluid'];

/** A DTCG colour token -> a `Color`.
 *
 * `components` is authoritative and the optional `hex` is ignored entirely. The
 * spec says the components win, and it happens to be the right way round for
 * us: re-parsing the fallback would make a lossy serialization the source of a
 * number the contrast maths depends on. */
function toColor(token: Tokens['color']['bg']): Color {
  const [r, g, b] = token.$value.components;
  // `noUncheckedIndexedAccess` is on and the schema pins the array to exactly
  // three items, which the type system states as `number[]` — so the three are
  // narrowed here rather than asserted with `!`.
  if (r === undefined || g === undefined || b === undefined) {
    throw new Error('from-record: a colour token has fewer than three components');
  }
  return {
    r: Math.round(r * CHANNEL_MAX),
    g: Math.round(g * CHANNEL_MAX),
    b: Math.round(b * CHANNEL_MAX),
    a: token.$value.alpha ?? 1,
  };
}

function toPalette(color: Tokens['color']): Palette {
  return {
    bg: toColor(color.bg),
    bgElevated: toColor(color.bgElevated),
    ink: toColor(color.ink),
    inkMuted: toColor(color.inkMuted),
    inkFaint: toColor(color.inkFaint),
    accent: toColor(color.accent),
    accentSoft: toColor(color.accentSoft),
    veil: toColor(color.veil),
    hairline: toColor(color.hairline),
  };
}

/** The registry, inverted: family name -> id.
 *
 * The record stores the *name* (`Fraunces`) because that is what a DTCG
 * `fontFamily` token means and what a designer's tool round-trips. The renderer
 * wants the id (`fraunces`), because an id is what the self-hosted `@fontsource`
 * import in `globals.css` is keyed by. */
const FAMILY_TO_ID = new Map<string, FontFamilyId>(
  (Object.entries(FONT_REGISTRY) as [FontFamilyId, { family: string }][]).map(
    ([id, entry]) => [entry.family, id],
  ),
);

const FONT_SLOTS: readonly FontSlot[] = ['display', 'text'];
const TYPE_ROLES: readonly TypeRoleKey[] = [
  'hero',
  'section',
  'lead',
  'normal',
  'muted',
  'eyebrow',
  'stat',
];

/** The stored vocabularies, until phase 02 makes motion its own table read.
 *
 * `defaultMotion` is already a stored string rather than a `Literal`, so this
 * lookup is where an unknown one is caught — and it is a `Map` rather than a
 * `switch` so that phase 02 replaces a data structure instead of unpicking a
 * branch. `REDUCED_MOTION` is deliberately not in here: it is not a choice an
 * art direction gets to make, it is the wrapper reading the environment. */
const MOTION_BY_ID = new Map<string, MotionVocabulary>([
  ['cinematic', CINEMATIC_MOTION],
  ['editorial', EDITORIAL_MOTION],
]);

function toLength(length: Fluid['rhythm']['measure']): Length {
  return { value: length.value, unit: length.unit };
}

function toClamp(size: Fluid['type']['hero']['size']): ClampTriple {
  return {
    min: toLength(size.min),
    preferred: toLength(size.preferred),
    max: toLength(size.max),
  };
}

function toTypeScale(
  fluid: Fluid['type'],
  dtcg: Tokens['type'],
): Record<TypeRoleKey, TypeRole> {
  const entries = TYPE_ROLES.map((role): [TypeRoleKey, TypeRole] => {
    const f = fluid[role];
    const d = dtcg[role];
    // `weight` is a DTCG `fontWeight`, so the schema types it as any integer
    // 1-1000 — which is what the spec allows and wider than the three weights
    // the registry actually self-hosts. Narrowed here rather than trusted: a
    // token asking for 300 would render as a synthesized face, which looks
    // like a font bug and is a data bug.
    const weight = d.weight.$value;
    return [
      role,
      {
        font: f.font,
        size: toClamp(f.size),
        leading: d.leading.$value,
        tracking: d.tracking.$value,
        weight: narrowWeight(weight),
        ...(f.case ? { case: f.case } : {}),
        ...(f.color ? { color: f.color } : {}),
      },
    ];
  });
  return Object.fromEntries(entries) as Record<TypeRoleKey, TypeRole>;
}

const REGISTERED_WEIGHTS = [400, 500, 600] as const;
type RegisteredWeight = (typeof REGISTERED_WEIGHTS)[number];

function narrowWeight(weight: number): RegisteredWeight {
  const found = REGISTERED_WEIGHTS.find((w) => w === weight);
  if (found === undefined) {
    throw new Error(`from-record: no self-hosted face at weight ${String(weight)}`);
  }
  return found;
}

function toRhythm(fluid: Fluid['rhythm'], space: Tokens['space']): Rhythm {
  return {
    space: [
      toLength(space.step1.$value),
      toLength(space.step2.$value),
      toLength(space.step3.$value),
      toLength(space.step4.$value),
      toLength(space.step5.$value),
      toLength(space.step6.$value),
      toLength(space.step7.$value),
    ],
    scenePaddingY: toClamp(fluid.scenePaddingY),
    scenePaddingX: toClamp(fluid.scenePaddingX),
    measure: toLength(fluid.measure),
    contentMax: toLength(fluid.contentMax),
    // Spelled out rather than spread. The table is `Record<Layout, SceneFit>`
    // on this side and a record with one field per layout on the other, and
    // writing the six out is what makes adding a layout a compile error in both
    // languages instead of a key that quietly resolves to `undefined`.
    fit: {
      'full-bleed': fluid.fit['full-bleed'],
      'split-left': fluid.fit['split-left'],
      'split-right': fluid.fit['split-right'],
      centered: fluid.fit.centered,
      stack: fluid.fit.stack,
      grid: fluid.fit.grid,
    },
    fitMinBlock: toLength(fluid.fitMinBlock),
    fitPlace: fluid.fitPlace,
    fitScrollMargin: toLength(fluid.fitScrollMargin),
  };
}

function toTexture(layers: Fluid['texture']): Texture {
  return layers.map((layer) => toLayer(layer));
}

/** One texture layer. The discriminated union crosses the boundary intact —
 * both sides discriminate on `kind` — so this is a per-kind reconstruction
 * rather than a spread, which is what keeps a removed kind from surviving in
 * stored data and quietly coming back. */
function toLayer(layer: Fluid['texture'][number]): Texture[number] {
  const base = {
    intensity: layer.intensity,
    color: layer.color,
    scale: toLength(layer.scale),
    offset: toLength(layer.offset),
  };
  switch (layer.kind) {
    case 'grain':
      return { ...base, kind: 'grain', density: layer.density };
    case 'weave':
      return { ...base, kind: 'weave', density: layer.density };
    case 'halftone':
      return { ...base, kind: 'halftone', angle: layer.angle, steps: layer.steps };
    case 'hatch':
      return {
        ...base,
        kind: 'hatch',
        angle: layer.angle,
        cross: layer.cross,
        density: layer.density,
      };
    case 'dither':
      return { ...base, kind: 'dither', steps: layer.steps };
    case 'rule':
      return { ...base, kind: 'rule', axis: layer.axis, weight: layer.weight };
  }
}

function toImage(image: Fluid['image']): ImageTreatment {
  return {
    tone: image.tone,
    overlay: image.overlay ? toLayer(image.overlay) : null,
    frame: image.frame,
    edge: toLength(image.edge),
    veil: image.veil,
    ratios: image.ratios.map((r) => ({ w: r.w, h: r.h })),
  };
}

export interface ResolvedRecord {
  /** What it was resolved from, carried along rather than re-fetched. Publish
   * freezes this into the artifact; the renderer never looks at it. */
  record: ArtDirectionRecord;
  artDirection: ArtDirection;
  motion: MotionVocabulary;
}

/** A record -> the two objects the renderer takes.
 *
 * A `Result`, because both failures it can hit are a stored value naming
 * something this build does not have — a font family, a motion vocabulary —
 * and that is a legitimate state of a system where the two are deployed
 * separately, not a bug in this process. The caller renders its empty state.
 *
 * The `throw`s inside the helpers above are the other half of that line: a
 * colour token with two components, or a weight the registry never self-hosted,
 * cannot survive the Zod parse this record already passed, so reaching one is a
 * bug in the validator rather than an expected failure (rule 3). */
export function fromRecord(record: ArtDirectionRecord): Result<ResolvedRecord> {
  const fonts: Partial<Record<FontSlot, FontFamilyId>> = {};
  for (const slot of FONT_SLOTS) {
    const name = record.tokens.font[slot].$value;
    const id = FAMILY_TO_ID.get(name);
    // The message names the slot, not the family: the family came from stored
    // data and this string reaches a log.
    if (id === undefined) {
      return err('invalid_input', `${record.id}: unregistered font family at ${slot}`);
    }
    fonts[slot] = id;
  }
  const display = fonts.display;
  const text = fonts.text;
  if (display === undefined || text === undefined) {
    throw new Error('from-record: a font slot went unfilled with no error raised');
  }

  const motion = MOTION_BY_ID.get(record.extensions.defaultMotion);
  if (motion === undefined) {
    return err('invalid_input', `${record.id}: unknown motion vocabulary`);
  }

  const fluid = record.extensions.fluid;
  return ok({
    record,
    artDirection: {
      id: record.id,
      color: toPalette(record.tokens.color),
      fonts: { display, text },
      type: toTypeScale(fluid.type, record.tokens.type),
      rhythm: toRhythm(fluid.rhythm, record.tokens.space),
      texture: toTexture(fluid.texture),
      image: toImage(fluid.image),
      visualBlend: fluid.visualBlend,
      visualStrength: record.tokens.visual.strength.$value,
    },
    motion,
  });
}

export { REDUCED_MOTION };
