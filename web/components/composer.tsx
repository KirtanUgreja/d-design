"use client";

// The first screen is the proof (docs/v4/ui-research.md, rule 1): one prompt
// box, a real brief as the placeholder, real example briefs as chips. No
// templates, no tour, no form above the prompt (docs/design/app.md § 1).
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { Chevron } from "@/components/chevron";
import { Button } from "@/components/ui/button";
import { api, type DeckKind, type DeckTone, type NewDeckOptions } from "@/lib/api/client";
import { authClient } from "@/lib/auth-client";

const KINDS: [DeckKind, string][] = [
  ["auto", "Any kind"],
  ["pitch", "Pitch"],
  ["sales", "Sales"],
  ["launch", "Launch"],
  ["investor_update", "Investor update"],
  ["partnership", "Partnership"],
  ["project", "Project (college)"],
];
const TONES: [DeckTone, string][] = [
  ["confident", "Confident"],
  ["plain", "Plain"],
  ["warm", "Warm"],
  ["bold", "Bold"],
];
const SLIDES = { min: 5, max: 15, start: 10 };

// A brief typed before signing in survives sign-up (phase 31, A5): kept in
// this tab only, with its settings, and started the moment the person is
// signed in.
const PENDING = "dd:pending-brief";

interface Pending {
  prompt: string;
  options: NewDeckOptions;
}

function remember(pending: Pending): void {
  try {
    sessionStorage.setItem(PENDING, JSON.stringify(pending));
  } catch {
    // storage blocked: the person retypes it; nothing breaks
  }
}

function takePending(): Pending | null {
  try {
    const raw = sessionStorage.getItem(PENDING);
    sessionStorage.removeItem(PENDING);
    if (!raw) return null;
    const v: unknown = JSON.parse(raw);
    if (typeof v !== "object" || v === null || !("prompt" in v) || typeof v.prompt !== "string") return null;
    const o: Record<string, unknown> = "options" in v && typeof v.options === "object" && v.options !== null ? { ...v.options } : {};
    // Read back like any stored input: only values the controls can produce.
    const kind = KINDS.find(([k]) => k === o.kind)?.[0];
    const tone = TONES.find(([t]) => t === o.tone)?.[0];
    const slides = typeof o.slides === "number" && o.slides >= SLIDES.min && o.slides <= SLIDES.max ? o.slides : undefined;
    return { prompt: v.prompt, options: { kind, tone, slides } };
  } catch {
    return null;
  }
}


interface Example {
  id: string;
  prompt: string;
  type: string;
  short: string; // a word or two for its chip: "Tessel 2"
}

const TYPE_LABEL: Record<string, string> = {
  pitch: "Pitch",
  sales: "Sales",
  launch: "Launch",
  investor_update: "Investor update",
  partnership: "Partnership",
  project: "Project",
  auto: "Pitch",
};

export function Composer({ examples }: { examples: Example[] }) {
  const router = useRouter();
  const [text, setText] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [kind, setKind] = useState<DeckKind>("auto");
  const [tone, setTone] = useState<DeckTone>("confident");
  const [slides, setSlides] = useState(SLIDES.start);
  const label = useId();

  const start = async () => {
    // Every start is a real deck, built by the API and the worker. An example
    // chip only fills the box (the recorded runs are gone: owner, 2026-10-10).
    if (!text.trim()) {
      setNotice("Say what you're presenting first, or pick an example below.");
      return;
    }
    setNotice(null);
    const options: NewDeckOptions = { kind, tone, slides };
    const session = await authClient.getSession();
    if (!session.data) {
      remember({ prompt: text.trim(), options });
      router.push(`/sign-up?next=${encodeURIComponent("/")}`);
      return;
    }
    await create(text.trim(), options);
  };

  const create = async (brief: string, options: NewDeckOptions) => {
    const made = await api.create(brief, options);
    if (made.ok) {
      router.push(`/d/${made.value.id}`);
      return;
    }
    setNotice(made.error);
  };

  // Back from sign-up or sign-in with a brief waiting: start it.
  useEffect(() => {
    let live = true;
    const resume = async () => {
      const session = await authClient.getSession();
      if (!live || !session.data) return;
      const pending = takePending();
      if (!pending) return;
      setText(pending.prompt);
      await create(pending.prompt, pending.options);
    };
    void resume();
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once, on arrival
  }, []);

  return (
    <form
      className="flex min-w-0 flex-col gap-6"
      onSubmit={(e) => {
        e.preventDefault();
        void start();
      }}
    >
      <div className="flex flex-col items-center gap-3 text-center">
        <label
          htmlFor={label}
          className="font-display text-[clamp(2.25rem,4.6vw,3.5rem)] leading-[1.06] tracking-[-0.02em] text-balance"
        >
          What are you <em>presenting</em>?
        </label>
        <p className="max-w-[52ch] text-[15px] text-ink-2 sm:text-base">
          Type a brief. Get a deck that looks designed, with every slide checked in a real browser and every number sourced.
        </p>
      </div>
      <div className="border border-ink bg-paper transition-colors focus-within:border-accent focus-within:ring-1 focus-within:ring-accent">
        <textarea
          id={label}
          autoFocus
          rows={3}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setNotice(null);
          }}
          placeholder="Seed pitch for our CI tool, to early-stage investors. Add your numbers, your ask, anything slide by slide."
          className="block min-h-[8.5rem] w-full resize-none bg-transparent px-5 pt-4 pb-3 text-[17px] leading-[1.55] outline-none placeholder:text-ink-2/55 focus-visible:outline-none sm:px-6"
        />
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3 border-t border-rule px-5 py-3 sm:px-6">
          <Choice label="Kind" value={kind} options={KINDS} onChange={setKind} />
          <Stepper value={slides} onChange={setSlides} />
          <Choice label="Tone" value={tone} options={TONES} onChange={setTone} />
          <Button type="submit" size="lg" className="ml-auto px-6">
            Start <span aria-hidden="true">→</span>
          </Button>
        </div>
      </div>
      {notice && (
        <p role="status" className="border-l-2 border-flag pl-3 text-sm">
          {notice}
        </p>
      )}
      {examples.length > 0 && (
        <div className="flex flex-wrap items-center justify-center gap-x-2 gap-y-2">
          <span className="mr-1 text-[13px] text-ink-2">Try</span>
          {examples.map((x) => (
            <button
              key={x.id}
              type="button"
              onClick={() => {
                setText(x.prompt);
                setNotice(null);
                document.getElementById(label)?.focus();
              }}
              className="flex items-baseline gap-1.5 border border-rule px-3 py-1.5 text-[13px] transition-colors hover:border-ink"
            >
              <span className="text-ink-2">{TYPE_LABEL[x.type] ?? "Deck"} ·</span>
              <span>{x.short}</span>
            </button>
          ))}
        </div>
      )}
    </form>
  );
}

function Choice<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: [T, string][];
  onChange: (v: T) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-[13px]">
      <span className="text-ink-2">{label}</span>
      <span className="relative">
        <select
          value={value}
          onChange={(e) => {
            const next = options.find(([v]) => v === e.target.value);
            if (next) onChange(next[0]);
          }}
          className="cursor-pointer appearance-none border-b border-rule bg-transparent py-1 pr-5 pl-0.5 font-medium text-ink outline-none hover:border-ink focus-visible:border-ink"
        >
          {options.map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
        <Chevron className="pointer-events-none absolute top-1/2 right-0.5 -translate-y-1/2 text-ink-2" />
      </span>
    </label>
  );
}

function Stepper({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const step = "grid size-6 place-content-center border border-rule text-ink transition-colors hover:border-ink disabled:opacity-35";
  return (
    <div role="group" aria-label="Number of slides" className="flex items-center gap-2 text-[13px]">
      <span className="text-ink-2">Slides</span>
      <button type="button" aria-label="Fewer slides" className={step} disabled={value <= SLIDES.min} onClick={() => onChange(value - 1)}>
        −
      </button>
      <span className="w-5 text-center font-medium tabular-nums" aria-live="polite">
        {value}
      </span>
      <button type="button" aria-label="More slides" className={step} disabled={value >= SLIDES.max} onClick={() => onChange(value + 1)}>
        +
      </button>
    </div>
  );
}
