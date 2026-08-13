/**
 * GENERATED FILE — do not hand-edit.
 *
 * Source of truth: api/schema/*.py (Pydantic). Regenerate with
 * `pnpm schema:generate`. A hand-edit here fails the gate
 * (docs/coderules/python.md -> "Generated TypeScript is never hand-edited").
 */
import { z } from 'zod';

const BrandKitSchema = z.object({
  colors: z.string().max(300).optional(),
  fonts: z.string().max(300).optional(),
  vibe: z.string().max(300).optional(),
});

export const BriefSchema = z.object({
  topic: z.string().min(1).max(500),
  slide_count: z.number().min(1).max(40),
  audience: z.string().max(500).optional(),
  goal: z.string().max(500).optional(),
  brand_kit: BrandKitSchema.optional(),
  extra_info: z.string().max(2000).optional(),
});

export type Brief = z.infer<typeof BriefSchema>;
