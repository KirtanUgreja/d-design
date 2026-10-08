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
import type { Recording } from "@/lib/fixtures";
import type { Fact, Plan, Provenance } from "@/lib/types";

const CHIP: Record<Provenance, string> = {
  YOU: "From your brief",
  WEB: "From a cited source — click to read it",
  AI: "Written by the AI",
};

// What the gate reads: a recording, or a live deck mapped to the same shapes.
export type GateDeck = Pick<Recording, "id" | "thesis" | "questions" | "outline" | "facts">;
export type Decisions = Record<string, "approved" | "cut">;

export function OutlineGate({
  deck,
  onApprove,
  style,
  thesis = true,
}: {
  deck: GateDeck;
  // The live deck's style card (phase 39); recordings have none.
  style?: React.ReactNode;
  // Live decks save the decisions and start the build; recordings replay.
  onApprove?: (decided: Decisions, order: string[]) => void;
  // Off when the page's own header already carries the thesis.
  thesis?: boolean;
}) {
  const router = useRouter();
  const facts = useMemo(() => new Map(deck.facts.map((f) => [f.id, f])), [deck.facts]);
  const [slides, setSlides] = useState<Plan[]>(deck.outline);
  const [asked, setAsked] = useState(0);
  const [decided, setDecided] = useState<Decisions>({});

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

  const approve = () =>
    onApprove
      ? onApprove(
          decided,
          slides.map((s) => s.id),
        )
      : router.push(`/deck/${deck.id}/watch`);
  const interviewing = asked < deck.questions.length;

  return (
    <main className="mx-auto grid max-w-[1440px] gap-10 px-4 py-8 sm:px-8 lg:grid-cols-[minmax(0,1fr)_360px] lg:gap-16 lg:py-10">
      <section aria-labelledby="outline-title" className="min-w-0">
        {thesis ? (
          <>
            <p className="placard">The one thing they should remember</p>
            <h1
              id="outline-title"
              className="mt-2 max-w-3xl font-display text-[26px] leading-[1.15] tracking-[-0.015em] sm:text-[32px]"
            >
              {deck.thesis}
            </h1>
          </>
        ) : (
          <h2 id="outline-title" className="font-display text-[24px] leading-tight">
            The outline · {slides.length} slides
          </h2>
        )}
        <p className="mt-3 max-w-2xl text-[13px] text-ink-2">
          Move slides, or open a source to read where a line came from. Lines without a mark were written by the AI;{" "}
          <span className="font-medium text-ink">YOU</span> is from your brief,{" "}
          <span className="font-medium text-ink">WEB</span> from a cited source.
        </p>
        <ol className="mt-6 border-t border-rule">
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
      </section>
      <aside className="flex min-w-0 flex-col gap-8 lg:sticky lg:top-[72px] lg:max-h-[calc(100dvh-88px)] lg:self-start lg:overflow-y-auto lg:pb-2">
        {interviewing ? (
          <Interview
            deck={deck}
            asked={asked}
            onNext={() => setAsked((n) => n + 1)}
            onSkip={() => setAsked(deck.questions.length)}
          />
        ) : (
          (style ?? <InterviewDone />)
        )}
        <div className="flex flex-col gap-3 border-t border-ink pt-5">
          <Button size="lg" className="w-full" disabled={pending.length > 0} onClick={approve}>
            Approve outline
          </Button>
          <p className="text-[13px] leading-snug text-ink-2" aria-live="polite">
            {pending.length > 0
              ? `${pending.length} number${pending.length > 1 ? "s" : ""} without a source. Keep or cut ${pending.length > 1 ? "them" : "it"} first.`
              : "Nothing is generated until you approve. The deck takes about two minutes, and you can watch it arrive."}
          </p>
        </div>
      </aside>
    </main>
  );
}

function InterviewDone() {
  return (
    <div className="flex flex-col gap-2">
      <p className="placard">Interview done</p>
      <p className="text-sm text-ink-2">When the outline says what you mean, approve it.</p>
    </div>
  );
}

function Interview({
  deck,
  asked,
  onNext,
  onSkip,
}: {
  deck: GateDeck;
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
  if (!q) return <InterviewDone />;
  return (
    <section className="flex flex-col gap-5" aria-labelledby="question">
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
    </section>
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
    <li className="group grid grid-cols-[2rem_minmax(0,1fr)_auto] gap-x-4 border-b border-rule py-5 sm:grid-cols-[2.5rem_minmax(0,1fr)_auto]">
      <span className="pt-4 font-display text-xl leading-none text-ink-2 tabular-nums" aria-hidden="true">
        {index + 1}
      </span>
      <div className="flex min-w-0 flex-col gap-1.5">
        <p className="placard">
          {plan.beat}
          {plan.hasChart ? " · chart" : ""}
        </p>
        {headline && (
          <p className="text-[17px] leading-snug font-medium text-ink">
            {headline.text} <Chip plan={plan} name="headline" facts={facts} factIds={headline.factIds} />
          </p>
        )}
        {rest.length > 0 && (
          <ul className="flex flex-wrap gap-x-2 text-sm leading-snug text-ink-2">
            {rest.map((f, i) => (
              <li key={f.name} className="flex items-baseline gap-x-2">
                {i > 0 && (
                  <span aria-hidden="true" className="text-rule">
                    ·
                  </span>
                )}
                <span>
                  {f.text}
                  <Chip plan={plan} name={f.name} facts={facts} factIds={f.factIds} />
                </span>
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
      <div className="flex flex-col items-end gap-1 pt-3">
        {fixed ? (
          <span className="placard">{index === 0 ? "Cover" : "The ask"}</span>
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
  // AI is the default and goes unmarked (the legend says so). YOU and WEB are
  // the claims worth noticing.
  if (kind === "AI") return null;
  const badge = (
    <Badge variant="outline" className="ml-1 align-middle text-[10px] font-medium tracking-wider">
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
