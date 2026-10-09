"use client";

// The deck's style, seen before the build (docs/v4/plan/39-design-reset.md § 6):
// one generated style, its colours and type, and Another style to draw a new
// one. Never a menu of looks (owner, 2026-10-05). No slide thumbnails: they
// were drawn by the code-built layout and showed every style as the same old
// slide (owner, 2026-10-10); the designed slides come from the build.
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, type StyleCard as Card } from "@/lib/api/client";

const POLL_MS = 1500;
const POLL_LIMIT = 40; // about a minute: thumbnails take seconds, not minutes

// `drawn` names what the thumbnails show (the brand colours): a change redraws them.
export function StyleCard({ deckId, drawn = "" }: { deckId: string; drawn?: string }) {
  const [card, setCard] = useState<Card | null>(null);
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);
  const [version, setVersion] = useState(0);

  // Fetch the card once the worker has made it; a new version fetches again.
  useEffect(() => {
    let live = true;
    const poll = async () => {
      for (let i = 0; i < POLL_LIMIT && live; i++) {
        const got = await api.style(deckId);
        if (!live) return;
        if (got.ok) {
          setCard(got.value);
          return;
        }
        await new Promise((r) => setTimeout(r, POLL_MS));
      }
    };
    void poll();
    return () => {
      live = false;
    };
  }, [deckId, version, drawn]);

  // New colours: the old thumbnails are stale until the worker redraws them.
  const [seen, setSeen] = useState(drawn);
  if (seen !== drawn) {
    setSeen(drawn);
    setCard(null);
    setVersion((v) => v + 1);
  }

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
      {card ? (
        <>
          <div className="flex h-24 overflow-hidden border border-rule" aria-label="Palette">
            {Object.entries(card.colors).map(([role, hex]) => (
              <span key={role} title={role} className="flex-1" style={{ backgroundColor: hex }} />
            ))}
          </div>
          <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1.5 border-t border-rule pt-3 text-[13px]">
            <dt className="text-ink-2">Type</dt>
            <dd className="truncate">
              {card.display} · {card.text}
            </dd>
            {card.imageStyle && (
              <>
                <dt className="text-ink-2">Images</dt>
                <dd className="leading-snug">{card.imageStyle}</dd>
              </>
            )}
          </dl>
          <p className="text-[13px] leading-snug text-ink-2">
            Each slide is designed one by one in the build, in this style. Nothing is drawn from a template.
          </p>
        </>
      ) : (
        <Skeleton className="h-24 w-full" />
      )}
      {problem && <p className="text-sm text-destructive">{problem}</p>}
    </section>
  );
}
