// A deck on the wall: its cover once it is built, otherwise its one sentence
// on paper, with a placard saying where it stands.
import Link from "next/link";

import { Placard } from "@/components/placard";
import { SlideThumb } from "@/components/slide-thumb";
import { api } from "@/lib/api/client";
import { STATUS_LABEL, type DeckRow } from "@/lib/decks";

export function DeckCard({ deck }: { deck: DeckRow }) {
  const label = STATUS_LABEL[deck.status] ?? deck.status;
  return (
    <Link href={`/d/${deck.id}`} className="group block">
      {deck.cover ? (
        <SlideThumb src={api.thumb(deck.id, deck.cover, deck.version)} alt={`The cover of: ${deck.title}`} />
      ) : (
        <div className="flex aspect-video flex-col justify-end border border-rule bg-paper-2 p-4 sm:p-5">
          <p className="line-clamp-3 font-display text-lg leading-snug text-ink-2">{deck.title}</p>
        </div>
      )}
      <Placard label={label} aside={deck.slides ? `${deck.slides} slides` : undefined} flag={deck.status === "error"} />
      <p className="mt-1 line-clamp-2 text-sm leading-snug underline-offset-4 group-hover:underline">{deck.title}</p>
    </Link>
  );
}
