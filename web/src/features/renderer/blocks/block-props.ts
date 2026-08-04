// `Block['props']` is the discriminated union; the individual member types
// are not a named export of `@/schema` (same reasoning as
// art-direction/cinematic-dark.ts's `PropsOf<T>`: it keeps the schema's
// public surface small and this projection can never drift from it, because
// there is nothing to drift from — it's the same union, narrowed).

import type { Block } from '@/schema';

type PropsOf<T extends Block['props']['type']> = Extract<Block['props'], { type: T }>;

export type EyebrowProps = PropsOf<'eyebrow'>;
export type HeadlineProps = PropsOf<'headline'>;
export type BodyProps = PropsOf<'body'>;
export type QuoteProps = PropsOf<'quote'>;
export type ListProps = PropsOf<'list'>;
export type StatProps = PropsOf<'stat'>;
export type ImageProps = PropsOf<'image'>;
export type VideoProps = PropsOf<'video'>;
export type CtaProps = PropsOf<'cta'>;
export type AbstractVisualProps = PropsOf<'abstract-visual'>;
export type SlotProps = PropsOf<'slot'>;
