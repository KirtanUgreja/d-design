"use client";

// Match the colour: a minute's play on the account page (owner, 2026-10-10:
// "add some mini game"). A target swatch, three sliders in OKLCH (the space
// the deck palettes are built in), and a score from the distance between the
// two in OKLab, the way the palette engine measures colour. The best score
// stays in this browser only.
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

interface Lch {
  l: number; // 0..1
  c: number; // 0..0.3
  h: number; // 0..360
}

const BEST = "dd:colour-best";

const css = ({ l, c, h }: Lch) => `oklch(${l.toFixed(3)} ${c.toFixed(3)} ${h.toFixed(1)})`;

function lab({ l, c, h }: Lch): [number, number, number] {
  const r = (h * Math.PI) / 180;
  return [l, c * Math.cos(r), c * Math.sin(r)];
}

/** Distance in OKLab, times 100: about 2 is the smallest difference most people see. */
function distance(a: Lch, b: Lch): number {
  const [l1, a1, b1] = lab(a);
  const [l2, a2, b2] = lab(b);
  return Math.hypot(l1 - l2, a1 - a2, b1 - b2) * 100;
}

function target(): Lch {
  return { l: 0.45 + Math.random() * 0.4, c: 0.06 + Math.random() * 0.12, h: Math.random() * 360 };
}

function readBest(): number {
  try {
    const n = Number(localStorage.getItem(BEST));
    return Number.isFinite(n) ? n : 0;
  } catch {
    return 0;
  }
}

function verdict(score: number): string {
  if (score >= 95) return "Print-shop eye.";
  if (score >= 85) return "Art-director close.";
  if (score >= 70) return "Close. Check the hue.";
  if (score >= 50) return "In the family.";
  return "Different colour. Try the lightness first.";
}

export function ColourGame() {
  // The same first colour on the server and in the browser; a random one once mounted.
  const [goal, setGoal] = useState<Lch>({ l: 0.62, c: 0.13, h: 40 });
  const [mine, setMine] = useState<Lch>({ l: 0.65, c: 0.1, h: 180 });
  const [score, setScore] = useState<number | null>(null);
  const [best, setBest] = useState(0);
  const [round, setRound] = useState(1);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- browser-only values, read once on mount
    setGoal(target());
    setBest(readBest());
  }, []);

  const check = () => {
    const s = Math.max(0, Math.round(100 - distance(goal, mine) * 3));
    setScore(s);
    if (s > best) {
      setBest(s);
      try {
        localStorage.setItem(BEST, String(s));
      } catch {
        // storage blocked: the best score lasts this visit only
      }
    }
  };
  const next = () => {
    setGoal(target());
    setScore(null);
    setRound((r) => r + 1);
  };

  return (
    <section aria-labelledby="game" className="flex flex-col gap-5 border border-rule p-5 sm:p-6">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id="game" className="font-display text-2xl tracking-tight">
          Match the colour
        </h2>
        <p className="placard">
          Round {round} · best {best}
        </p>
      </div>
      <p className="-mt-2 text-sm text-ink-2">Mix the right swatch until it matches the left one, then check how close you are.</p>
      <div className="grid grid-cols-2 overflow-hidden border border-rule">
        <div className="flex aspect-[4/3] items-end p-3" style={{ backgroundColor: css(goal) }}>
          <span className="bg-paper/85 px-1.5 py-0.5 font-mono text-[10px] tracking-wide uppercase">Target</span>
        </div>
        <div className="flex aspect-[4/3] items-end justify-end p-3" style={{ backgroundColor: css(mine) }}>
          <span className="bg-paper/85 px-1.5 py-0.5 font-mono text-[10px] tracking-wide uppercase">
            {score === null ? "Yours" : css(goal).replace("oklch", "was oklch")}
          </span>
        </div>
      </div>
      <div className="flex flex-col gap-3">
        <Slider label="Lightness" min={0.2} max={0.95} step={0.005} value={mine.l} onChange={(l) => setMine((m) => ({ ...m, l }))} disabled={score !== null} />
        <Slider label="Colourfulness" min={0} max={0.25} step={0.002} value={mine.c} onChange={(c) => setMine((m) => ({ ...m, c }))} disabled={score !== null} />
        <Slider label="Hue" min={0} max={360} step={1} value={mine.h} onChange={(h) => setMine((m) => ({ ...m, h }))} disabled={score !== null} />
      </div>
      <div className="flex min-h-11 flex-wrap items-center gap-x-5 gap-y-2" aria-live="polite">
        {score === null ? (
          <Button onClick={check}>Check</Button>
        ) : (
          <>
            <p className="flex items-baseline gap-2">
              <span className="font-display text-[34px] leading-none tabular-nums">{score}</span>
              <span className="text-sm text-ink-2">{verdict(score)}</span>
            </p>
            <Button variant="outline" className="ml-auto" onClick={next}>
              Next colour
            </Button>
          </>
        )}
      </div>
    </section>
  );
}

function Slider({
  label,
  min,
  max,
  step,
  value,
  onChange,
  disabled,
}: {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (v: number) => void;
  disabled: boolean;
}) {
  return (
    <label className="grid grid-cols-[7.5rem_minmax(0,1fr)] items-center gap-3 text-[13px]">
      <span className="text-ink-2">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[var(--color-accent)] disabled:opacity-50"
      />
    </label>
  );
}
