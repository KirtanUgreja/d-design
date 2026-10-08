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

  const thumbs = card?.previews ?? [];
  return (
    <section aria-labelledby="style-title" className="flex flex-col gap-4">
      <div className="flex items-baseline justify-between gap-4">
        <p className="placard">Your deck&apos;s style</p>
        <Button variant="link" size="sm" className="h-auto px-0 text-ink" onClick={another} disabled={busy || !card}>
          Another style
        </Button>
      </div>
      <div>
        <h2 id="style-title" className="font-display text-[26px] leading-tight tracking-[-0.01em]">
          {card ? card.name : "Drawing your style…"}
        </h2>
        {card && <p className="mt-1 text-sm leading-snug text-ink-2">{card.idea}</p>}
      </div>
      <div className="grid grid-cols-2 gap-2">
        {thumbs.length > 0
          ? thumbs.map((name, i) => (
              // eslint-disable-next-line @next/next/no-img-element -- a same-origin screenshot from our API
              <img
                key={name}
                src={api.styleThumb(deckId, name, version)}
                alt={i === 0 ? "Your cover in this style" : "A slide of your deck in this style"}
                className={`aspect-video w-full border border-rule bg-paper-2 object-cover ${i === 0 ? "col-span-2" : ""}`}
              />
            ))
          : [0, 1, 2].map((n) => <Skeleton key={n} className={`aspect-video w-full ${n === 0 ? "col-span-2" : ""}`} />)}
      </div>
      {card && (
        <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1.5 border-t border-rule pt-3 text-[13px]">
          <dt className="text-ink-2">Type</dt>
          <dd className="truncate">
            {card.display} · {card.text}
          </dd>
          <dt className="text-ink-2">Colour</dt>
          <dd className="flex items-center gap-1.5" aria-label="Palette">
            {Object.entries(card.colors).map(([role, hex]) => (
              <span key={role} title={role} className="size-4 rounded-full border border-rule" style={{ backgroundColor: hex }} />
            ))}
          </dd>
          {card.imageStyle && (
            <>
              <dt className="text-ink-2">Images</dt>
              <dd className="leading-snug">{card.imageStyle}</dd>
            </>
          )}
        </dl>
      )}
      {problem && <p className="text-sm text-destructive">{problem}</p>}
    </section>
  );
}
