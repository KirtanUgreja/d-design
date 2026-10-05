"use client";

// The interview and the outline gate, one screen (docs/design/app.md § 2):
// the cheapest place in the product to fix anything, and the trust surface.
// Provenance on every field, sources one click away, unsourced numbers held
// until a person decides (docs/v4/ui-research.md, rules 4 and 8).
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import type { Fact, Plan, Provenance, Recording } from "@/lib/fixtures";

const CHIP: Record<Provenance, string> = {
  YOU: "From your brief",
  WEB: "From a cited source",
  AI: "Written by the AI",
};

export function OutlineGate({ deck }: { deck: Recording }) {
  const router = useRouter();
  const facts = useMemo(() => new Map(deck.facts.map((f) => [f.id, f])), [deck.facts]);
  const [slides, setSlides] = useState<Plan[]>(deck.outline);
  const [asked, setAsked] = useState(0);
  const [decided, setDecided] = useState<Record<string, "approved" | "cut">>({});

  const pending = deck.facts.filter(
    (f) => f.status === "proposed" && !decided[f.id] && slides.some((s) => s.fields.some((x) => x.factIds.includes(f.id))),
  );

  const move = (from: number, to: number) => {
    if (to < 1 || to > slides.length - 2 || from === 0 || from === slides.length - 1) return; // the ends are fixed
    setSlides((all) => {
      const next = [...all];
      const [it] = next.splice(from, 1);
      if (it) next.splice(to, 0, it);
      return next;
    });
  };

  return (
    <main className="grid min-h-[calc(100dvh-57px)] md:grid-cols-[minmax(320px,4fr)_8fr]">
      <Interview deck={deck} asked={asked} onNext={() => setAsked((n) => n + 1)} onSkip={() => setAsked(deck.questions.length)} />
      <section aria-labelledby="outline-title" className="border-l border-rule px-8 py-8">
        <p className="text-sm text-ink-2">The one thing they should remember</p>
        <h1 id="outline-title" className="mb-8 max-w-3xl font-display text-3xl leading-tight">
          {deck.thesis}
        </h1>
        <ol className="grid gap-3">
          {slides.map((s, i) => (
            <SlideCard
              key={s.id}
              plan={s}
              index={i}
              total={slides.length}
              facts={facts}
              decided={decided}
              onDecide={(id, d) => setDecided((m) => ({ ...m, [id]: d }))}
              onMove={(to) => move(i, to)}
            />
          ))}
        </ol>
        <div className="sticky bottom-0 mt-8 flex items-center justify-between border-t border-rule bg-paper py-4">
          <p className="text-sm text-ink-2" aria-live="polite">
            {pending.length > 0
              ? `${pending.length} number${pending.length > 1 ? "s" : ""} without a source. Approve, add a source, or cut ${pending.length > 1 ? "them" : "it"} first.`
              : "Nothing is generated until you approve. This step costs almost nothing to redo."}
          </p>
          <button
            type="button"
            disabled={pending.length > 0}
            onClick={() => router.push(`/deck/${deck.id}/look`)}
            className="rounded-[var(--radius-chrome)] bg-accent px-6 py-2.5 text-sm font-medium text-accent-ink disabled:opacity-40"
          >
            Approve outline
          </button>
        </div>
      </section>
    </main>
  );
}

function Interview({ deck, asked, onNext, onSkip }: { deck: Recording; asked: number; onNext: () => void; onSkip: () => void }) {
  const [answer, setAnswer] = useState("");
  const q = deck.questions[asked];
  if (!q) {
    return (
      <aside className="px-8 py-8">
        <p className="text-sm text-ink-2">Interview done</p>
        <p className="mt-2">
          Change anything on the right: drag to reorder, or read where each line came from. When it says what you mean,
          approve it.
        </p>
      </aside>
    );
  }
  return (
    <aside className="px-8 py-8" aria-labelledby="question">
      <p className="text-sm text-ink-2">
        {asked + 1} of {deck.questions.length}
      </p>
      <h2 id="question" className="mt-2 font-display text-2xl leading-snug">
        {q.question}
      </h2>
      <ul className="mt-5 grid gap-2">
        {q.suggestions.map((s) => (
          <li key={s}>
            <button
              type="button"
              onClick={() => {
                setAnswer("");
                onNext();
              }}
              className="w-full rounded-[var(--radius-chrome)] border border-rule px-3 py-2 text-left text-sm hover:border-ink"
            >
              {s}
            </button>
          </li>
        ))}
      </ul>
      <form
        className="mt-4 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setAnswer("");
          onNext();
        }}
      >
        <label className="sr-only" htmlFor="own-answer">
          Your own answer
        </label>
        <input
          id="own-answer"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Or in your own words"
          className="min-w-0 flex-1 border-b border-ink bg-transparent py-2 outline-none"
        />
        <button type="submit" className="text-sm underline">
          Next
        </button>
      </form>
      <button type="button" onClick={onSkip} className="mt-8 text-sm text-ink-2 underline">
        Skip the rest — use what I gave you
      </button>
    </aside>
  );
}

function SlideCard({
  plan,
  index,
  total,
  facts,
  decided,
  onDecide,
  onMove,
}: {
  plan: Plan;
  index: number;
  total: number;
  facts: Map<string, Fact>;
  decided: Record<string, "approved" | "cut">;
  onDecide: (factId: string, d: "approved" | "cut") => void;
  onMove: (to: number) => void;
}) {
  const headline = plan.fields.find((f) => f.name === "headline");
  const rest = plan.fields.filter((f) => f.name !== "headline" && f.name !== "source");
  const fixed = index === 0 || index === total - 1;
  return (
    <li className="grid grid-cols-[2.5rem_1fr_auto] gap-4 border border-rule bg-paper px-4 py-4">
      <span className="font-display text-xl text-ink-2" aria-hidden="true">
        {index + 1}
      </span>
      <div className="min-w-0">
        <p className="text-xs uppercase tracking-wider text-ink-2">
          {plan.beat}
          {plan.hasChart ? " · chart" : ""}
        </p>
        {headline && (
          <p className="mt-1 text-lg leading-snug">
            {headline.text} <Chip plan={plan} name="headline" facts={facts} factIds={headline.factIds} />
          </p>
        )}
        {rest.length > 0 && (
          <ul className="mt-2 grid gap-1 text-sm text-ink-2">
            {rest.map((f) => (
              <li key={f.name}>
                {f.text} <Chip plan={plan} name={f.name} facts={facts} factIds={f.factIds} />
              </li>
            ))}
          </ul>
        )}
        {plan.fields
          .flatMap((f) => f.factIds)
          .map((id) => facts.get(id))
          .filter((f): f is Fact => !!f && f.status === "proposed" && !decided[f.id])
          .map((f) => (
            <div key={f.id} role="group" aria-label="Number without a source" className="mt-3 border-l-2 border-flag pl-3 text-sm">
              <p>
                <strong>{f.value}</strong> has no source.
              </p>
              <div className="mt-1 flex gap-4">
                <button type="button" className="underline" onClick={() => onDecide(f.id, "approved")}>
                  Keep as illustrative
                </button>
                <button type="button" className="underline" onClick={() => onDecide(f.id, "cut")}>
                  Cut it
                </button>
              </div>
            </div>
          ))}
      </div>
      <div className="flex flex-col gap-1">
        {fixed ? (
          <span className="text-xs text-ink-2">{index === 0 ? "Cover" : "The ask"}</span>
        ) : (
          <>
            <button type="button" aria-label={`Move slide ${index + 1} up`} onClick={() => onMove(index - 1)} className="px-2 text-ink-2 hover:text-ink">
              ↑
            </button>
            <button type="button" aria-label={`Move slide ${index + 1} down`} onClick={() => onMove(index + 1)} className="px-2 text-ink-2 hover:text-ink">
              ↓
            </button>
          </>
        )}
      </div>
    </li>
  );
}

function Chip({ plan, name, facts, factIds }: { plan: Plan; name: string; facts: Map<string, Fact>; factIds: string[] }) {
  const kind: Provenance = plan.provenance[name] ?? "AI";
  const cited = factIds.map((id) => facts.get(id)).filter((f): f is Fact => !!f && f.source === "cited" && !!f.citation);
  const popId = `src-${plan.id}-${name}`;
  const label = (
    <span className="ml-1 rounded-[2px] border border-rule px-1 align-middle font-mono text-[10px] tracking-wider text-ink-2">
      {kind}
    </span>
  );
  if (kind !== "WEB" || cited.length === 0) {
    return <abbr title={CHIP[kind]} className="no-underline">{label}</abbr>;
  }
  return (
    <>
      <button type="button" popoverTarget={popId} aria-label={`${CHIP.WEB}: show the source`} className="align-middle">
        {label}
      </button>
      <div id={popId} popover="auto" className="m-auto max-w-lg border border-ink bg-paper p-5 text-sm text-ink shadow-none">
        {cited.map((f) => (
          <figure key={f.id} className="mb-4 last:mb-0">
            <blockquote className="font-display text-base">“{f.citation?.quote}”</blockquote>
            <figcaption className="mt-2 text-ink-2">
              {f.citation?.publisher || f.citation?.title}
              {f.asOf ? `, ${f.asOf}` : ""} ·{" "}
              <a href={f.citation?.url} target="_blank" rel="noreferrer noopener" className="underline">
                open the page
              </a>
              {f.flags.length > 0 && <span className="block text-flag">{f.flags.join(" · ")}</span>}
            </figcaption>
          </figure>
        ))}
      </div>
    </>
  );
}
