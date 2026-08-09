// The public surface. Everything outside this feature imports from here, not
// from a sibling file directly (docs/coderules/structure.md).

export type {
  ArtDirection,
  ArtDirectionId,
  ClampTriple,
  ColorRole,
  Density,
  FontFamilyId,
  FontSlot,
  FontWeight,
  Layout,
  Length,
  Palette,
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

export { CINEMATIC_DARK } from './cinematic-dark';
export { EDITORIAL_LIGHT } from './editorial-light';

// The way to get an art direction from an id. Both constants above stay
// exported for the places that legitimately name one — the fixtures, the
// tests, and the dev harnesses that show them side by side — but product code
// that has an `Experience` should resolve rather than pick.
export type { ResolvedArtDirection } from './resolve-art-direction';
export { ART_DIRECTION_IDS, resolveArtDirection } from './resolve-art-direction';

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
