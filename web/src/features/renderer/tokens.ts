// Blocks never hold a hex code or a px value — they reference a CSS custom
// property that `to-css-vars.ts` already emitted onto the scene root. This
// file only builds the *names* of those variables (the wire contract
// `to-css-vars.ts` and this file both agree on); it never re-derives a value.
// docs/v1/plan/04-renderer.md -> Search: "to-css-vars — the only token->string
// path. Do not write a second one."

import type { CSSProperties } from 'react';

import type { ArtDirection, Layout, TypeRoleKey } from '@/features/art-direction';
import { COLOR_VAR } from '@/features/art-direction';

// Re-exported, not re-declared. `to-css-vars.ts` emits these names and this
// file reads them, so the two have to agree — and an agreement kept in two
// places is a drift waiting for the first renamed property. It moved next to
// `Palette` in phase 14, when the texture layers needed the same mapping to
// turn a colour *role* into a variable reference.
export { COLOR_VAR };

export interface TypeStyle {
  fontFamily: string;
  fontSize: string;
  lineHeight: string;
  letterSpacing: string;
  fontWeight: string;
  textTransform?: 'uppercase';
  color: string;
  overflowWrap: 'anywhere';
}

/** `emphasis` (or a block's implicit role) selects a type role, nothing else
 * — the block never sees a font size or a color. `overflowWrap: 'anywhere'`
 * is load-bearing, not decoration: hostile.json's "xxxx…" run has no spaces
 * for a normal line-break to land on, and at `hero` size an unbreakable run
 * overflows the viewport on both sides without it — found by that fixture,
 * fixed here once for every text block rather than per block. */
export function typeStyle(role: TypeRoleKey, ad: ArtDirection): TypeStyle {
  const def = ad.type[role];
  return {
    fontFamily: `var(--font-${def.font})`,
    fontSize: `var(--type-${role}-size)`,
    lineHeight: `var(--type-${role}-leading)`,
    letterSpacing: `var(--type-${role}-tracking)`,
    fontWeight: `var(--type-${role}-weight)`,
    ...(def.case === 'uppercase' ? { textTransform: 'uppercase' as const } : {}),
    color: COLOR_VAR[def.color ?? 'ink'],
    overflowWrap: 'anywhere',
  };
}

export function spaceVar(index: 1 | 2 | 3 | 4 | 5 | 6 | 7): string {
  return `var(--space-${index})`;
}

/** How the AbstractVisual generators composite onto the ground.
 *
 * A `var()` rather than a literal, because `screen` — keep only what is lighter
 * — is a near-black-ground assumption, and the seven places that hardcoded it
 * turned every generator into a smudge the first time an art direction had a
 * white ground. The value is the art direction's `visualBlend` token.
 *
 * Cast because React types `mixBlendMode` as the CSS keyword union, which a
 * `var()` reference is not — the same cast `SceneRenderer` already makes for
 * the custom-property bundle, and for the same reason. */
export const VISUAL_BLEND = 'var(--visual-blend)' as CSSProperties['mixBlendMode'];

/** An AbstractVisual layer's opacity: the generator's own intensity, scaled by
 * the art direction's `visualStrength`. A `calc()` rather than a number, so the
 * token stays a token — the generators never read the art direction object, the
 * same way no block does. */
export function visualOpacity(intensity: number): string {
  return `calc(${intensity} * var(--visual-strength))`;
}

export const SCENE_PADDING_BLOCK = 'var(--scene-padding-y)';
export const SCENE_PADDING_INLINE = 'var(--scene-padding-x)';
export const MEASURE = 'var(--measure)';
export const CONTENT_MAX = 'var(--content-max)';

/** The frame a scene of this layout gets, as a variable *name* — the art
 * direction already resolved `viewport`/`content` into a length or `auto` in
 * `to-css-vars.ts`. Keyed by `layout`, which is something the AI writes, so
 * this stays a lookup and never becomes a branch on a token's value (rule 20,
 * docs/v2/plan/13-scene-fit.md). */
export function sceneMinBlockVar(layout: Layout): string {
  return `var(--scene-min-block-${layout})`;
}

/** The raw frame length, before the per-layout `viewport`/`content` answer is
 * applied. Read directly only by things that are not scenes and have no
 * content to be measured against — the `Slot` iframe is the one case. */
export const SCENE_FIT_MIN_BLOCK = 'var(--scene-fit-min-block)';

export const SCENE_PLACE = 'var(--scene-place)';
export const SCENE_SCROLL_MARGIN = 'var(--scene-scroll-margin)';

/** A texture layer's value, by position in the art direction's layer list.
 *
 * Indexed rather than keyed by kind, because two layers of the same kind is
 * the arrangement riso misregistration is made of, and `--texture-halftone-*`
 * cannot hold two of them. Field names are the ones `to-css-vars.ts` emits;
 * which fields exist depends on the kind, which is why the caller is a
 * component that already switched on it. */
export function textureVar(index: number, field: string): string {
  return `var(--texture-${index}-${field})`;
}
