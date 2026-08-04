// The public surface. Everything outside this feature imports from here, not
// from a sibling file directly (docs/coderules/structure.md).

export type {
  ArtDirection,
  ClampTriple,
  FontRegistryId,
  Length,
  Palette,
  Rhythm,
  Texture,
  TextureLayer,
  TypeRole,
  TypeRoleKey,
  Unit,
} from './cinematic-dark';
export { CINEMATIC_DARK, FONT_REGISTRY } from './cinematic-dark';

export type { Color } from './color';
export { toCssColor } from './color';

export type {
  Easing,
  MotionIntent,
  MotionIntentDef,
  MotionVocabulary,
} from './motion-vocabulary';
export { CINEMATIC_MOTION, REDUCED_MOTION, staggerDelayMs } from './motion-vocabulary';

export type { ResolvedPalette } from './resolve-brand';
export { resolveBrand } from './resolve-brand';

export { toCssVars } from './to-css-vars';
