"use client";

// The user's logo for this deck (phase 38): picked at the outline gate, checked
// by the worker (never trusted as uploaded), then placed by code on the cover
// and the ask where it reads on the ground.
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { api, type LiveDeck } from "@/lib/api/client";

const MAX_BYTES = 2_000_000;

function base64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    reader.onerror = () => reject(new Error("unreadable"));
    reader.readAsDataURL(file);
  });
}

// onChange must be stable (a useCallback): the polling effect depends on it.
export function LogoPicker({ deck, onChange }: { deck: LiveDeck; onChange: () => unknown }) {
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);
  const [shown, setShown] = useState(0); // bumps when the checked logo is ready

  // After an upload the worker checks the file; poll until it is ready or refused.
  useEffect(() => {
    if (deck.logo === "none") return;
    let live = true;
    const poll = async () => {
      for (let i = 0; i < 20 && live; i++) {
        const res = await fetch(api.logoUrl(deck.id, i));
        if (!live) return;
        if (res.ok) {
          setShown(i + 1);
          return;
        }
        if (i % 3 === 2) void onChange(); // a refusal arrives on the deck
        await new Promise((r) => setTimeout(r, 1500));
      }
    };
    void poll();
    return () => {
      live = false;
    };
  }, [deck.id, deck.logo, deck.version, onChange]);

  const pick = async (file: File | undefined) => {
    if (!file) return;
    setProblem("");
    if (file.size > MAX_BYTES) return setProblem("A logo file is at most 2 MB.");
    setBusy(true);
    const sent = await api.uploadLogo(deck.id, await base64(file).catch(() => ""));
    setBusy(false);
    if (!sent.ok) return setProblem(sent.error);
    setShown(0);
    onChange();
  };

  return (
    <div className="flex flex-wrap items-center gap-3 text-sm">
      {deck.logo !== "none" && shown > 0 && (
        // eslint-disable-next-line @next/next/no-img-element -- our own checked PNG
        <img src={api.logoUrl(deck.id, shown)} alt="Your logo" className="h-8 w-auto border border-rule bg-paper p-1" />
      )}
      <label className="cursor-pointer underline underline-offset-4">
        {deck.logo === "none" ? "Add your logo" : "Replace the logo"}
        <input
          type="file"
          accept="image/png,image/jpeg,image/webp,image/svg+xml"
          className="sr-only"
          disabled={busy}
          onChange={(e) => void pick(e.target.files?.[0])}
        />
      </label>
      {deck.logo !== "none" && (
        <Button variant="ghost" size="sm" onClick={() => void api.removeLogo(deck.id).then(onChange)}>
          Remove
        </Button>
      )}
      <span className="text-muted-foreground">
        {deck.logo !== "none" && shown === 0 && !deck.logoNote ? "Checking the file…" : "On the cover and the ask."}
      </span>
      {(problem || deck.logoNote) && <p className="w-full text-destructive">{problem || deck.logoNote}</p>}
    </div>
  );
}
