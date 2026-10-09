"use client";

// The person's own screenshots or demo images (2026-10-09): up to six, shown on
// the deck's demo, product and user-flow slides instead of a generated picture.
// Checked and re-encoded by the worker, never shown as uploaded.
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api, type LiveDeck } from "@/lib/api/client";

const MAX_BYTES = 2_000_000;
const MAX = 6;

function base64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    reader.onerror = () => reject(new Error("unreadable"));
    reader.readAsDataURL(file);
  });
}

// onChange must be stable (a useCallback): the polling effect depends on it.
export function ScreensPicker({ deck, onChange }: { deck: LiveDeck; onChange: () => unknown }) {
  const [caption, setCaption] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState("");
  const waiting = deck.screens.some((s) => !s.ready && !s.note);

  // While the worker checks an upload, read the deck again until it is done.
  useEffect(() => {
    if (!waiting) return;
    const t = setInterval(() => void onChange(), 1500);
    return () => clearInterval(t);
  }, [waiting, onChange]);

  const pick = async (file: File | undefined) => {
    if (!file) return;
    setProblem("");
    if (file.size > MAX_BYTES) return setProblem("A screenshot is at most 2 MB.");
    setBusy(true);
    const sent = await api.addScreen(deck.id, await base64(file).catch(() => ""), caption);
    setBusy(false);
    if (!sent.ok) return setProblem(sent.error);
    setCaption("");
    onChange();
  };

  return (
    <section aria-labelledby="screens-title" className="flex flex-col gap-3 border-t border-rule pt-4">
      <p id="screens-title" className="placard">
        Your screenshots
      </p>
      <p className="text-[13px] leading-snug text-ink-2">
        Screens of your product or project. They go on the demo and user-flow slides, framed, instead of a generated picture.
      </p>
      {deck.screens.length > 0 && (
        <ul className="grid grid-cols-3 gap-2">
          {deck.screens.map((s, i) => (
            <li key={`${i}-${s.caption}`} className="flex flex-col gap-1">
              <div className="flex aspect-video items-center justify-center overflow-hidden border border-rule bg-paper-2">
                {s.ready ? (
                  // eslint-disable-next-line @next/next/no-img-element -- our own re-encoded webp
                  <img src={api.screenUrl(deck.id, i + 1, deck.version)} alt={s.caption || `Screenshot ${i + 1}`} className="size-full object-cover" />
                ) : (
                  <span className="px-1 text-center text-[11px] text-ink-2">{s.note ? "Can't use it" : "Checking…"}</span>
                )}
              </div>
              <div className="flex items-center justify-between gap-1">
                <span className="truncate text-[12px] text-ink-2">{s.caption || `Screen ${i + 1}`}</span>
                <Button
                  variant="link"
                  size="sm"
                  className="h-auto px-0 text-[12px] text-ink-2"
                  disabled={busy}
                  onClick={() => void api.removeScreen(deck.id, i + 1).then(onChange)}
                >
                  Remove
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {deck.screens.length < MAX && (
        <div className="flex flex-wrap items-center gap-2">
          <input
            aria-label="What it shows (optional)"
            placeholder="What it shows (optional)"
            value={caption}
            maxLength={120}
            onChange={(e) => setCaption(e.target.value)}
            className="h-9 min-w-0 flex-1 border-b border-rule bg-transparent text-sm outline-none placeholder:text-ink-2/70 focus:border-ink"
          />
          <label className="cursor-pointer text-sm underline underline-offset-4">
            {busy ? "Adding…" : "Add a screenshot"}
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              className="sr-only"
              disabled={busy}
              onChange={(e) => void pick(e.target.files?.[0])}
            />
          </label>
        </div>
      )}
      {deck.screens.filter((s) => s.note).map((s, i) => (
        <p key={i} className="text-sm text-flag">{s.note}</p>
      ))}
      {problem && <p className="text-sm text-flag">{problem}</p>}
    </section>
  );
}
