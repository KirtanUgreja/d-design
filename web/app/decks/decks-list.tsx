"use client";
// Your decks: every deck as its cover (or its sentence, before it is built),
// newest first, each opening where it stands.
import Link from "next/link";
import { useEffect, useState } from "react";

import { DeckCard } from "@/components/deck-card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { loadDecks, type DeckRow } from "@/lib/decks";
import type { Result } from "@/lib/result";

export function DecksList() {
  const [decks, setDecks] = useState<Result<DeckRow[]> | null>(null);

  useEffect(() => {
    let live = true;
    void loadDecks().then((r) => live && setDecks(r ?? { ok: false, error: "Sign in to see your decks." }));
    return () => {
      live = false;
    };
  }, []);

  if (decks === null) {
    return (
      <ul className="grid gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
        {[0, 1, 2].map((i) => (
          <li key={i} className="flex flex-col gap-3">
            <Skeleton className="aspect-video w-full" />
            <Skeleton className="h-4 w-2/3" />
          </li>
        ))}
      </ul>
    );
  }
  if (!decks.ok) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{decks.error}</AlertDescription>
      </Alert>
    );
  }
  if (decks.value.length === 0) {
    return (
      <Empty className="border border-rule py-16">
        <EmptyHeader>
          <EmptyTitle className="font-display text-2xl">No decks yet</EmptyTitle>
          <EmptyDescription>Type a brief and your first deck shows up here.</EmptyDescription>
        </EmptyHeader>
        <EmptyContent>
          <Button asChild>
            <Link href="/">Start a deck</Link>
          </Button>
        </EmptyContent>
      </Empty>
    );
  }
  return (
    <ul className="grid gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
      {decks.value.map((d) => (
        <li key={d.id}>
          <DeckCard
            deck={d}
            onDeleted={() => setDecks((r) => (r?.ok ? { ok: true, value: r.value.filter((x) => x.id !== d.id) } : r))}
          />
        </li>
      ))}
    </ul>
  );
}
