"use client";

// Pick a look (docs/design/app.md § 3): their own words in three far-apart
// looks, a free instant shuffle, and nothing to configure. Three distinct
// choices, never a gallery (docs/v4/ui-research.md -> choice overload).
import { useRouter } from "next/navigation";
import { useState } from "react";

import { SlideThumb } from "@/components/slide-thumb";
import type { Look, Recording } from "@/lib/fixtures";
import { Button } from "@/components/ui/button";

const PALETTE: Record<string, string> = {
  paper: "ink on paper",
  night: "dark, one spot colour",
  duotone: "two-colour print",
  blocks: "colour fields",
  tonal: "one hue, tonal",
  signal: "black, white and a signal",
  deep: "deep tonal",
};

const pairingName = (look: Look) => `${look.fonts[0] ?? ""} with ${look.fonts[1] ?? ""}`;

export function LookPicker({ deck }: { deck: Recording }) {
  const router = useRouter();
  const sets = [deck.looks.slice(0, 3), deck.looks.slice(3, 6)].filter((s) => s.length === 3);
  const [set, setSet] = useState(0);
  const looks = sets[set] ?? sets[0] ?? [];
  return (
    <main className="px-8 py-8">
      <div className="mb-6 flex items-end justify-between gap-6">
        <div>
          <h1 className="font-display text-3xl">Pick a look</h1>
          <p className="mt-1 text-sm text-ink-2">
            Your own headline, set three ways. These are previews; every slide is composed for the look you pick.
          </p>
        </div>
        <Button variant="outline" size="lg" onClick={() => setSet((n) => (n + 1) % sets.length)}>
          Shuffle
        </Button>
      </div>
      <ul className="grid gap-8 md:grid-cols-3">
        {looks.map((look) => (
          <li key={look.id}>
            <button
              type="button"
              onClick={() => router.push(`/deck/${deck.id}/watch?look=${encodeURIComponent(look.id)}`)}
              className="group block w-full text-left"
              aria-label={`Use this look: ${pairingName(look)}, ${PALETTE[look.palette] ?? look.palette}`}
            >
              <div className="grid gap-2 outline-offset-4 group-hover:outline group-hover:outline-1 group-hover:outline-ink">
                {look.tiles.map((t) => (
                  <SlideThumb key={t} src={`/fixtures/${deck.id}/${t}`} alt="" />
                ))}
              </div>
              <p className="mt-3 text-sm">{pairingName(look)}</p>
              <p className="text-xs text-ink-2">
                {PALETTE[look.palette] ?? look.palette} · {look.grid} grid · {look.motif}
              </p>
            </button>
          </li>
        ))}
      </ul>
      <p className="mt-6 text-xs text-ink-2">Prototype: this deck was recorded in the first look of the first set.</p>
    </main>
  );
}
