/**
 * GENERATED FILE — do not hand-edit.
 *
 * Source of truth: api/schema/*.py (Pydantic). Regenerate with
 * `pnpm schema:generate`. A hand-edit here fails the gate
 * (docs/coderules/python.md -> "Generated TypeScript is never hand-edited").
 */
import { z } from 'zod';

const OutlineClaimSchema = z.object({
  text: z.string().min(1).max(240),
  source: z.union([z.literal('user'), z.literal('model')]),
});

const OutlineSectionSchema = z.object({
  heading: z.string().min(1).max(120),
  summary: z.string().min(1).max(400),
  claims: z.array(OutlineClaimSchema).min(1).max(20),
});

export const OutlineSchema = z.object({
  title: z.string().min(1).max(120),
  audience: z.string().min(1).max(300),
  goal: z.string().min(1).max(300),
  sections: z.array(OutlineSectionSchema).min(1).max(12),
  must_haves: z.array(z.string()).max(10).optional(),
});

export type Outline = z.infer<typeof OutlineSchema>;
