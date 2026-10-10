"use client";
// The home page's second row, for a signed-in person: their latest decks, so
// a second visit opens their work (docs/design/app.md -> First run). Signed
// out, or with no decks yet, it shows nothing: the composer is the invitation.
import Link from "next/link";
import { useEffect, useState } from "react";

import { DeckCard } from "@/components/deck-card";
import { loadDecks, type DeckRow } from "@/lib/decks";

const SHOWN = 4;

export function YourDecks() {
  const [decks, setDecks] = useState<DeckRow[]>([]);
  useEffect(() => {
    let live = true;
    void loadDecks().then((r) => {
      if (live && r?.ok) setDecks(r.value);
    });
    return () => {
      live = false;
    };
  }, []);
  if (decks.length === 0) return null;
  return (
    <section aria-labelledby="your-decks" className="border-t border-rule pt-12 pb-16">
      <div className="mb-6 flex items-baseline justify-between gap-4">
        <h2 id="your-decks" className="font-display text-[28px] tracking-[-0.015em]">
          Your decks
        </h2>
        {decks.length > SHOWN && (
          <Link href="/decks" className="text-sm text-ink-2 underline-offset-4 hover:text-ink hover:underline">
            All {decks.length} decks →
          </Link>
        )}
      </div>
      <ul className="grid gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
        {decks.slice(0, SHOWN).map((d) => (
          <li key={d.id}>
            <DeckCard deck={d} onDeleted={() => setDecks((all) => all.filter((x) => x.id !== d.id))} />
          </li>
        ))}
      </ul>
    </section>
  );
}
