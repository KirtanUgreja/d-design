/**
 * GENERATED FILE — do not hand-edit.
 *
 * Source of truth: api/schema/*.py (Pydantic). Regenerate with
 * `pnpm schema:generate`. A hand-edit here fails the gate
 * (docs/coderules/python.md -> "Generated TypeScript is never hand-edited").
 */
import { z } from 'zod';

const ChartSeriesSchema = z.object({
  label: z.string().min(1).max(80),
  value: z.number(),
});

const ChartBlockSchema = z.object({
  kind: z.literal('chart'),
  chart_type: z.union([z.literal('bar'), z.literal('line'), z.literal('donut')]),
  title: z.string().min(1).max(120),
  series: z.array(ChartSeriesSchema).min(1).max(12),
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

const LayoutRegionSchema = z.object({
  role: z.union([
    z.literal('headline'),
    z.literal('body'),
    z.literal('media'),
    z.literal('stats'),
    z.literal('quote'),
    z.literal('chart'),
    z.literal('aside'),
  ]),
  span: z.union([
    z.literal('full'),
    z.literal('two-thirds'),
    z.literal('half'),
    z.literal('third'),
    z.literal('quarter'),
  ]),
  emphasis: z.union([z.literal('primary'), z.literal('secondary'), z.literal('quiet')]).optional(),
});

const LayoutStructureSchema = z.object({
  regions: z.array(LayoutRegionSchema).min(1).max(6),
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
  layout: LayoutStructureSchema,
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

export type ChartSeries = z.infer<typeof ChartSeriesSchema>;

export type ChartBlock = z.infer<typeof ChartBlockSchema>;

export type Cta = z.infer<typeof CtaSchema>;

export type ImageBlock = z.infer<typeof ImageBlockSchema>;

export type LayoutRegion = z.infer<typeof LayoutRegionSchema>;

export type LayoutStructure = z.infer<typeof LayoutStructureSchema>;

export type QuoteBlock = z.infer<typeof QuoteBlockSchema>;

export type TextBlock = z.infer<typeof TextBlockSchema>;

export type StatBlock = z.infer<typeof StatBlockSchema>;

export type Slide = z.infer<typeof SlideSchema>;
