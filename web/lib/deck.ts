import "server-only";

import { notFound } from "next/navigation";

import { loadRecording, type Recording } from "@/lib/fixtures";

export type DeckParams = { params: Promise<{ id: string }> };

/** The recording behind a deck route, or the 404 page. */
export async function getDeck({ params }: DeckParams): Promise<Recording> {
  const { id } = await params;
  const r = await loadRecording(id);
  if (!r.ok) notFound();
  return r.value;
}
