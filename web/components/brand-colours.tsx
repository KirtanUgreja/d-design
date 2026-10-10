"use client";

// The user's own colour (owner, 2026-10-09): the deck's palette is built around
// it, its lightness fitted for contrast. The logo's main colour is offered, never
// applied on its own. Set before the build, like the logo.
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { api, type LiveDeck } from "@/lib/api/client";

const HEX = /^#[0-9a-fA-F]{6}$/;

export function BrandColours({ deck, onChange }: { deck: LiveDeck; onChange: () => unknown }) {
  const current = deck.brand[0] ?? "";
  const [value, setValue] = useState(current || deck.logoColour || "#3f5220");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState("");

  const save = async (colors: string[]) => {
    setBusy(true);
    setProblem("");
    const done = await api.setBrand(deck.id, colors);
    setBusy(false);
    if (!done.ok) return setProblem(done.error);
    onChange();
  };

  const valid = HEX.test(value);
  const offer = deck.logoColour && deck.logoColour.toLowerCase() !== current ? deck.logoColour : "";
  return (
    <section aria-labelledby="brand-title" className="flex flex-col gap-3 border-t border-rule pt-4">
      <div className="flex items-baseline justify-between gap-4">
        <p id="brand-title" className="placard">
          Your colour
        </p>
        {current && (
          <Button variant="link" size="sm" className="h-auto px-0 text-ink-2" disabled={busy} onClick={() => void save([])}>
            Use generated colours
          </Button>
        )}
      </div>
      <p className="text-[13px] leading-snug text-ink-2">
        {current
          ? "The palette is built around your colour. Its lightness may shift a little so text stays readable."
          : "Give your brand colour and the palette is built around it."}
      </p>
      <div className="flex items-center gap-2">
        <label className="relative size-10 shrink-0 cursor-pointer border border-rule" style={{ backgroundColor: valid ? value : "transparent" }}>
          <span className="sr-only">Pick a colour</span>
          <input
            type="color"
            value={valid ? value : "#000000"}
            onChange={(e) => setValue(e.target.value)}
            className="absolute inset-0 size-full cursor-pointer opacity-0"
          />
        </label>
        <input
          aria-label="Colour as hex"
          value={value}
          onChange={(e) => setValue(e.target.value.trim())}
          spellCheck={false}
          className="h-10 w-28 border border-rule bg-transparent px-2.5 font-mono text-sm uppercase outline-none focus:border-ink"
        />
        <Button
          variant="outline"
          className="h-10"
          disabled={busy || !valid || value.toLowerCase() === current}
          onClick={() => void save([value.toLowerCase()])}
        >
          {busy ? "Applying…" : "Apply"}
        </Button>
      </div>
      {offer && (
        <button
          type="button"
          onClick={() => setValue(offer)}
          className="flex items-center gap-2 self-start text-[13px] text-ink-2 underline-offset-4 hover:text-ink hover:underline"
        >
          <span className="size-4 border border-rule" style={{ backgroundColor: offer }} aria-hidden="true" />
          Use your logo&apos;s colour ({offer.toUpperCase()})
        </button>
      )}
      {problem && <p className="text-sm text-flag">{problem}</p>}
    </section>
  );
}
