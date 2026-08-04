// Blocks never hold a hex code or a px value — they reference a CSS custom
// property that `to-css-vars.ts` already emitted onto the scene root. This
// file only builds the *names* of those variables (the wire contract
// `to-css-vars.ts` and this file both agree on); it never re-derives a value.
// docs/v1/plan/04-renderer.md -> Search: "to-css-vars — the only token->string
// path. Do not write a second one."

import type { ArtDirection, Palette, TypeRoleKey } from '@/features/art-direction';

export const COLOR_VAR: Record<keyof Palette, string> = {
  bg: 'var(--bg)',
  bgElevated: 'var(--bg-elevated)',
  ink: 'var(--ink)',
  inkMuted: 'var(--ink-muted)',
  inkFaint: 'var(--ink-faint)',
  accent: 'var(--accent)',
  accentSoft: 'var(--accent-soft)',
  veil: 'var(--veil)',
  hairline: 'var(--hairline)',
};

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

export const SCENE_PADDING_BLOCK = 'var(--scene-padding-y)';
export const SCENE_PADDING_INLINE = 'var(--scene-padding-x)';
export const MEASURE = 'var(--measure)';
export const CONTENT_MAX = 'var(--content-max)';

export function textureVar(kind: 'grain' | 'glow' | 'vignette'): string {
  return `var(--texture-${kind}-intensity)`;
}
