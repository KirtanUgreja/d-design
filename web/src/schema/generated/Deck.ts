/**
 * GENERATED FILE — do not hand-edit.
 *
 * Source of truth: api/schema/*.py (Pydantic). Regenerate with
 * `pnpm schema:generate`. A hand-edit here fails the gate
 * (docs/coderules/python.md -> "Generated TypeScript is never hand-edited").
 */
import { z } from 'zod';

const ChartBlockSchema = z.object({
  kind: z.literal('chart'),
  chart_type: z.union([z.literal('bar'), z.literal('line'), z.literal('donut')]),
  title: z.string().min(1).max(120),
  series: z
    .array(z.tuple([z.string(), z.number()]))
    .min(1)
    .max(12),
});

const CtaSchema = z.object({
  label: z.string().min(1).max(40),
  destination: z.string().min(1).max(2048),
});

const ImageBlockSchema = z.object({
  kind: z.literal('image'),
  subject: z.string().min(3).max(160),
  role: z.union([
    z.literal('background'),
    z.literal('hero'),
    z.literal('illustration'),
    z.literal('chart_companion'),
  ]),
  alt: z.string().min(3).max(240),
});

const QuoteBlockSchema = z.object({
  kind: z.literal('quote'),
  text: z.string().min(1).max(400),
  attribution: z.string().min(1).max(120),
});

const TextBlockSchema = z.object({
  kind: z.literal('text'),
  style: z.union([
    z.literal('headline'),
    z.literal('body'),
    z.literal('eyebrow'),
    z.literal('caption'),
  ]),
  content: z.string().min(1).max(500),
});

const StatBlockSchema = z.object({
  kind: z.literal('stat'),
  value: z.string().min(1).max(20),
  label: z.string().min(1).max(80),
});

const SlideSchema = z.object({
  id: z.string().regex(/^[a-z0-9-]+$/),
  title: z.string().min(1).max(120),
  layout_archetype: z.string().min(1).max(40),
  variant: z.string().max(40).optional(),
  blocks: z
    .array(
      z.discriminatedUnion('kind', [
        ImageBlockSchema,
        TextBlockSchema,
        StatBlockSchema,
        QuoteBlockSchema,
        ChartBlockSchema,
      ]),
    )
    .min(1)
    .max(12),
  cta: z.union([CtaSchema, z.null()]).optional(),
  motion_intent: z
    .union([
      z.literal('reveal'),
      z.literal('emphasize'),
      z.literal('transition'),
      z.literal('none'),
    ])
    .optional(),
});

export const DeckSchema = z.object({
  family_id: z.string().min(1).max(40),
  slides: z.array(SlideSchema).min(1).max(40),
});

export type Deck = z.infer<typeof DeckSchema>;
