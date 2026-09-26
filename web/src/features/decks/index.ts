/**
 * The decks feature — saving and reopening a deck (persistence).
 *
 * Generation is stateless: the deck lives in the browser until something
 * stores it. This is that something. api owns the `experiences` table, so the
 * payload schemas live here and the calls go through `decks.data.ts` — the
 * client never talks to api.
 *
 * Two shapes, deliberately. A **summary** is what the editor's deck list needs
 * (id, title, whether it is published); a **saved deck** carries the deck and
 * its image sidecar, which together are megabytes. Listing them all would move
 * every deck the user has ever made.
 */
import { z } from 'zod';

import { DeckSchema } from '../../schema/generated/Deck.js';

export type { Deck } from '../../schema/generated/Deck.js';

/** Image data URIs keyed by slide id — the sidecar the schema has no field for. */
export const ImagesSchema = z.record(z.string(), z.string());
export type Images = z.infer<typeof ImagesSchema>;

export const DeckSummarySchema = z.object({
  id: z.string(),
  title: z.string(),
  published_key: z.string().nullable(),
});
export type DeckSummary = z.infer<typeof DeckSummarySchema>;

/** What the browser posts to save: a real deck object, not api's JSON string.
 * The string is api's wire format and stays on the server side of this
 * boundary. */
export const SaveDeckSchema = z.object({
  title: z.string().min(1).max(120),
  deck: DeckSchema,
  images: ImagesSchema.default({}),
});
export type SaveDeckInput = z.infer<typeof SaveDeckSchema>;

export const SavedDeckSchema = z.object({
  id: z.string(),
  title: z.string(),
  deck: DeckSchema,
  images: ImagesSchema,
  published_key: z.string().nullable(),
});
export type SavedDeck = z.infer<typeof SavedDeckSchema>;
