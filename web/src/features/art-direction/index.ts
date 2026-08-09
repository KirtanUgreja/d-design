// The public surface — the client-safe half. Everything outside this feature
// imports from here or from `./server`, never from a sibling file directly
// (docs/coderules/structure.md).
//
// **Why this feature has two entry points, when the rule is one.** Every other
// feature's surface is pure or server-only throughout; this one is both. The
// renderer is a client component and imports these types and `toCssVars`; the
// art-direction *store* is a data module carrying `import 'server-only'`, whose
// whole job is to be a build error inside a client bundle. One barrel exporting
// both makes that build error fire on the renderer — which is the marker
// working exactly as designed, and it is telling us the surface is two things.
//
// So the split is by runtime, not by taste, and each half is still a single
// declared surface with nothing reachable around it:
//
//   index.ts   pure. Types, `fromRecord`, `toCssVars`, motion, brand resolution.
//              Runs in all three processes (rule 6) and in the browser.
//   server.ts  the reads. The store, and the seeded records off disk.
//
// What changed in v2 phase 01: this feature no longer *contains* any art
// direction. `CINEMATIC_DARK` and `EDITORIAL_LIGHT` were two exported constants
// and are now two rows, seeded by migration 0011 from
// `api/features/art_direction/seed.py`. What is left here is the shape of an
// art direction, the one place a token becomes a string, and the two ways to
// get one: `loadArtDirection` from the store, and `seededRecords` off disk for
// the harnesses and tests that have no store to read.

export type {
  ArtDirection,
  ClampTriple,
  ColorRole,
  Density,
  FontFamilyId,
  FontSlot,
  FontWeight,
  ImageFrame,
  ImageTone,
  ImageTreatment,
  Layout,
  Length,
  Palette,
  Ratio,
  Rhythm,
  RuleWeight,
  SceneFit,
  ScenePlace,
  Steps,
  Texture,
  TextureLayer,
  TypeRole,
  TypeRoleKey,
  Unit,
  VisualBlend,
  VisualStrength,
} from './art-direction';
export { COLOR_VAR, FONT_REGISTRY, LAYOUTS } from './art-direction';

// A stored record -> the two objects the renderer takes. The seam that replaced
// the constants, and a `Result` because a record naming a font family or a
// motion vocabulary this build does not have is a legitimate state, not a bug.
export type { ResolvedRecord } from './from-record';
export { fromRecord } from './from-record';

export type { Color } from './color';
// `relativeLuminance` is exported for one caller: the brand kit, which needs to
// say "on the light background" or "on the dark one" in plain words. Deriving
// that from the ground beats a `polarity: 'light' | 'dark'` token, which would
// be a second place the same fact lives and could disagree with the colour.
export { relativeLuminance, toCssColor } from './color';

export type {
  Easing,
  MotionIntent,
  MotionIntentDef,
  MotionVocabulary,
} from './motion-vocabulary';
export {
  CINEMATIC_MOTION,
  EDITORIAL_MOTION,
  REDUCED_MOTION,
  staggerDelayMs,
} from './motion-vocabulary';

export type { ResolvedPalette } from './resolve-brand';
export { resolveBrand } from './resolve-brand';

export { toCssVars } from './to-css-vars';
