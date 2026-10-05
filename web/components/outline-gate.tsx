"use client";

// The interview and the outline gate, one screen (docs/design/app.md § 2):
// the cheapest place in the product to fix anything, and the trust surface.
// Provenance on every field, sources one click away, unsourced numbers held
// until a person decides (docs/v4/ui-research.md, rules 4 and 8).
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Fact, Plan, Provenance, Recording } from "@/lib/fixtures";

const CHIP: Record<Provenance, string> = {
  YOU: "From your brief",
  WEB: "From a cited source — click to read it",
  AI: "Written by the AI",
};

export function OutlineGate({ deck }: { deck: Recording }) {
  const router = useRouter();
  const facts = useMemo(() => new Map(deck.facts.map((f) => [f.id, f])), [deck.facts]);
  const [slides, setSlides] = useState<Plan[]>(deck.outline);
  const [asked, setAsked] = useState(0);
  const [decided, setDecided] = useState<Record<string, "approved" | "cut">>({});

  const pending = deck.facts.filter(
    (f) =>
      f.status === "proposed" &&
      !decided[f.id] &&
      slides.some((s) => s.fields.some((x) => x.factIds.includes(f.id))),
  );

  const move = (from: number, to: number) => {
    // The cover and the ask are the fixed ends.
    if (to < 1 || to > slides.length - 2 || from === 0 || from === slides.length - 1) return;
    setSlides((all) => {
      const next = [...all];
      const [it] = next.splice(from, 1);
      if (it) next.splice(to, 0, it);
      return next;
    });
  };

  return (
    <main className="grid min-h-[calc(100dvh-57px)] md:grid-cols-[minmax(320px,4fr)_8fr]">
      <Interview
        deck={deck}
        asked={asked}
        onNext={() => setAsked((n) => n + 1)}
        onSkip={() => setAsked(deck.questions.length)}
      />
      <section aria-labelledby="outline-title" className="border-l border-rule px-8 py-8">
        <p className="text-sm text-muted-foreground">The one thing they should remember</p>
        <h1 id="outline-title" className="mb-8 max-w-3xl font-display text-3xl leading-tight">
          {deck.thesis}
        </h1>
        <ol className="flex flex-col gap-3">
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
        <div className="sticky bottom-0 mt-8 flex items-center justify-between gap-6 border-t border-rule bg-background py-4">
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {pending.length > 0
              ? `${pending.length} number${pending.length > 1 ? "s" : ""} without a source. Keep or cut ${pending.length > 1 ? "them" : "it"} first.`
              : "Nothing is generated until you approve. Your deck gets its own look, designed for these words."}
          </p>
          <Button size="lg" disabled={pending.length > 0} onClick={() => router.push(`/deck/${deck.id}/watch`)}>
            Approve outline
          </Button>
        </div>
      </section>
    </main>
  );
}

function Interview({
  deck,
  asked,
  onNext,
  onSkip,
}: {
  deck: Recording;
  asked: number;
  onNext: () => void;
  onSkip: () => void;
}) {
  const [answer, setAnswer] = useState("");
  const q = deck.questions[asked];
  const next = () => {
    setAnswer("");
    onNext();
  };
  if (!q) {
    return (
      <aside className="flex flex-col gap-2 px-8 py-8">
        <p className="text-sm text-muted-foreground">Interview done</p>
        <p>
          Change anything on the right: move slides, or read where each line came from. When it says what you mean,
          approve it.
        </p>
      </aside>
    );
  }
  return (
    <aside className="flex flex-col gap-5 px-8 py-8" aria-labelledby="question">
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">
          {asked + 1} of {deck.questions.length}
        </span>
        <span aria-hidden="true" className="h-px flex-1 bg-rule">
          <span className="block h-px bg-ink" style={{ width: `${(asked / deck.questions.length) * 100}%` }} />
        </span>
      </div>
      <h2 id="question" className="font-display text-2xl leading-snug">
        {q.question}
      </h2>
      <ul className="flex flex-col gap-2">
        {q.suggestions.map((s) => (
          <li key={s}>
            <Button variant="outline" className="h-auto w-full justify-start py-2.5 text-left whitespace-normal" onClick={next}>
              {s}
            </Button>
          </li>
        ))}
      </ul>
      <form
        className="flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          next();
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
        <Button type="submit" variant="ghost">
          Next
        </Button>
      </form>
      <Button variant="link" className="self-start px-0 text-muted-foreground" onClick={onSkip}>
        Skip the rest — use what I gave you
      </Button>
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
  const unsourced = plan.fields
    .flatMap((f) => f.factIds)
    .map((id) => facts.get(id))
    .filter((f): f is Fact => !!f && f.status === "proposed" && !decided[f.id]);
  return (
    <li className="group grid grid-cols-[2.5rem_1fr_auto] gap-4 border border-rule bg-background px-5 py-4 transition-colors hover:border-ink-2">
      <span className="font-display text-xl text-muted-foreground" aria-hidden="true">
        {index + 1}
      </span>
      <div className="flex min-w-0 flex-col gap-2">
        <p className="text-xs uppercase tracking-wider text-muted-foreground">
          {plan.beat}
          {plan.hasChart ? " · chart" : ""}
        </p>
        {headline && (
          <p className="text-lg leading-snug">
            {headline.text} <Chip plan={plan} name="headline" facts={facts} factIds={headline.factIds} />
          </p>
        )}
        {rest.length > 0 && (
          <ul className="flex flex-col gap-1 text-sm text-muted-foreground">
            {rest.map((f) => (
              <li key={f.name}>
                {f.text} <Chip plan={plan} name={f.name} facts={facts} factIds={f.factIds} />
              </li>
            ))}
          </ul>
        )}
        {unsourced.map((f) => (
          <Alert key={f.id} variant="destructive" className="mt-1">
            <AlertTitle>{f.value} has no source</AlertTitle>
            <AlertDescription className="flex gap-2 pt-1">
              <Button size="sm" variant="outline" onClick={() => onDecide(f.id, "approved")}>
                Keep as illustrative
              </Button>
              <Button size="sm" variant="ghost" onClick={() => onDecide(f.id, "cut")}>
                Cut it
              </Button>
            </AlertDescription>
          </Alert>
        ))}
      </div>
      <div className="flex flex-col items-end gap-1">
        {fixed ? (
          <Badge variant="outline">{index === 0 ? "Cover" : "The ask"}</Badge>
        ) : (
          <>
            <Button variant="ghost" size="icon-sm" aria-label={`Move slide ${index + 1} up`} onClick={() => onMove(index - 1)}>
              ↑
            </Button>
            <Button variant="ghost" size="icon-sm" aria-label={`Move slide ${index + 1} down`} onClick={() => onMove(index + 1)}>
              ↓
            </Button>
          </>
        )}
      </div>
    </li>
  );
}

function Chip({
  plan,
  name,
  facts,
  factIds,
}: {
  plan: Plan;
  name: string;
  facts: Map<string, Fact>;
  factIds: string[];
}) {
  const kind: Provenance = plan.provenance[name] ?? "AI";
  const cited = factIds
    .map((id) => facts.get(id))
    .filter((f): f is Fact => !!f && f.source === "cited" && !!f.citation);
  // AI is the default: a quiet mark. YOU and WEB are the claims worth noticing.
  const badge = (
    <Badge variant={kind === "AI" ? "ghost" : "outline"} className="ml-1 align-middle font-mono text-[10px] tracking-wider">
      {kind}
    </Badge>
  );
  if (kind === "WEB" && cited.length > 0) {
    return (
      <Popover>
        <PopoverTrigger aria-label={CHIP.WEB} className="align-middle">
          {badge}
        </PopoverTrigger>
        <PopoverContent className="w-96">
          {cited.map((f) => (
            <figure key={f.id} className="flex flex-col gap-2">
              <blockquote className="font-display text-base leading-snug">“{f.citation?.quote}”</blockquote>
              <figcaption className="text-muted-foreground">
                {f.citation?.publisher || f.citation?.title}
                {f.asOf ? `, ${f.asOf}` : ""} ·{" "}
                <a href={f.citation?.url} target="_blank" rel="noreferrer noopener" className="underline">
                  open the page
                </a>
                {f.flags.length > 0 && <span className="block text-destructive">{f.flags.join(" · ")}</span>}
              </figcaption>
            </figure>
          ))}
        </PopoverContent>
      </Popover>
    );
  }
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span tabIndex={0}>{badge}</span>
      </TooltipTrigger>
      <TooltipContent>{CHIP[kind]}</TooltipContent>
    </Tooltip>
  );
}
