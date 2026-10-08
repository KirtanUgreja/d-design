"use client";

// The deck's style, seen before the build (docs/v4/plan/39-design-reset.md § 6):
// one generated style with three slides in the deck's own words, and Another
// style to draw a new one. Never a menu of looks (owner, 2026-10-05).
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type StyleCard as Card } from "@/lib/api/client";

const POLL_MS = 1500;
const POLL_LIMIT = 40; // about a minute: thumbnails take seconds, not minutes

export function StyleCard({ deckId }: { deckId: string }) {
  const [card, setCard] = useState<Card | null>(null);
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);
  const [version, setVersion] = useState(0);

  // Poll until the worker has drawn the thumbnails; a new version restarts it.
  useEffect(() => {
    let live = true;
    const poll = async () => {
      for (let i = 0; i < POLL_LIMIT && live; i++) {
        const got = await api.style(deckId);
        if (!live) return;
        if (got.ok) {
          setCard(got.value);
          if (got.value.previews.length > 0) return;
        }
        await new Promise((r) => setTimeout(r, POLL_MS));
      }
    };
    void poll();
    return () => {
      live = false;
    };
  }, [deckId, version]);

  const another = async () => {
    setBusy(true);
    setProblem("");
    const done = await api.anotherStyle(deckId);
    setBusy(false);
    if (!done.ok) return setProblem(done.error);
    setCard(null);
    setVersion((v) => v + 1);
  };

  return (
    <section aria-labelledby="style-title" className="mb-8 flex flex-col gap-3 border-b border-rule pb-8">
      <div className="flex items-baseline justify-between gap-4">
        <div>
          <p className="text-sm text-muted-foreground">Your deck&apos;s style</p>
          <h2 id="style-title" className="font-display text-2xl">
            {card ? card.name : "Drawing your style…"}
          </h2>
          {card && <p className="max-w-2xl text-sm text-muted-foreground">{card.idea}</p>}
        </div>
        <Button variant="outline" onClick={another} disabled={busy || !card}>
          Another style
        </Button>
      </div>
      {card && (
        <p className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <span>
            {card.display} · {card.text}
          </span>
          <span className="flex gap-1" aria-label="Palette">
            {Object.entries(card.colors).map(([role, hex]) => (
              <span key={role} title={role} className="size-4 rounded-full border border-rule" style={{ backgroundColor: hex }} />
            ))}
          </span>
          {card.imageStyle && <span>Images: {card.imageStyle}</span>}
        </p>
      )}
      <div className="grid grid-cols-3 gap-3">
        {card && card.previews.length > 0
          ? card.previews.map((name) => (
              // eslint-disable-next-line @next/next/no-img-element -- a same-origin screenshot from our API
              <img
                key={name}
                src={api.styleThumb(deckId, name, version)}
                alt="A slide of your deck in this style"
                className="aspect-video w-full border border-rule object-cover"
              />
            ))
          : [0, 1, 2].map((n) => <Skeleton key={n} className="aspect-video w-full" />)}
      </div>
      {problem && <p className="text-sm text-destructive">{problem}</p>}
    </section>
  );
}
