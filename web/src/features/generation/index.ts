/**
 * The generation feature — the v1 pipeline, reachable from the editor (v3).
 *
 * Three stages, not one call, because the human gate sits between the first
 * two: the outline is shown and approved before anything is mapped or built
 * (v1 spec, the trust device — an invented claim is visible before a slide
 * is). The client holds the outline between calls, so neither side keeps
 * draft state.
 *
 * The payload schemas live here because every one of these shapes crosses a
 * process boundary twice: the browser posts to web, web posts to api, and api
 * returns model output. Each hop parses — one schema parse per external input,
 * at entry (AGENTS.md rule 2).
 */
import { z } from 'zod';

import { DeckSchema } from '../../schema/generated/Deck.js';
import { OutlineSchema } from '../../schema/generated/Outline.js';

export type { Deck } from '../../schema/generated/Deck.js';
export type { Outline } from '../../schema/generated/Outline.js';
export { OutlineSchema, DeckSchema };

export const StageSchema = z.enum(['interview', 'mapping', 'build']);
export type Stage = z.infer<typeof StageSchema>;

/** The user's typed brief — the interview's starting point, not the outline. */
export const BriefSchema = z.object({
  topic: z.string().min(1).max(500),
  slide_count: z.number().int().min(1).max(40),
  audience: z.string().max(500).default(''),
  goal: z.string().max(500).default(''),
});
export type Brief = z.infer<typeof BriefSchema>;

/** An approved outline plus the optional design family. Null means the
 * server's deterministic pick, so the same outline maps reproducibly. */
export const MappingInSchema = z.object({
  outline: OutlineSchema,
  family_id: z.string().nullable(),
});
export type MappingIn = z.infer<typeof MappingInSchema>;

export const BuildInSchema = z.object({
  deck: DeckSchema,
});
export type BuildIn = z.infer<typeof BuildInSchema>;

/** A built deck and its image assets. The images are data URIs the schema has
 * no field for; they ride beside the deck, keyed by slide id — the same key
 * the renderer's `images` prop reads. */
export const BuiltSchema = z.object({
  deck: DeckSchema,
  images: z.record(z.string(), z.string()),
});
export type Built = z.infer<typeof BuiltSchema>;
