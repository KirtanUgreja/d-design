"use client";

// The wait, made visible (2026-10-10). People rate a wait better when they
// can see the work being done (Buell & Norton, the labor illusion) and an
// anxious wait feels longer than an informed one, so every line here is real
// work the worker does, in order, with what it has found so far. Steps the
// stream cannot see yet advance on time, never past the real next event.
import { useEffect, useState } from "react";

import type { LiveEvent, LiveDeck } from "@/lib/api/client";
import { cn } from "@/lib/utils";

export function useElapsed(): number {
  const [start] = useState(() => Date.now());
  const [now, setNow] = useState(start);
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return Math.floor((now - start) / 1000);
}

export const clock = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

type State = "done" | "now" | "next";

interface Step {
  text: string;
  detail?: string;
  state: State;
}

// The questions and the outline: the steps of the interview and outline jobs.
export function Working({ status, research }: { status: LiveDeck["status"]; research: LiveEvent | null }) {
  const s = useElapsed();
  const found = research !== null;
  const steps: Step[] =
    status === "brief"
      ? [
          { text: "Reading your brief", state: s < 3 ? "now" : "done" },
          { text: "Writing a few questions only you can answer", state: s < 3 ? "next" : "now" },
        ]
      : [
          { text: "Reading your brief and your answers", state: s < 2 ? "now" : "done" },
          {
            text: "Searching the web for sources",
            state: found ? "done" : s < 2 ? "next" : "now",
            detail: found
              ? research.sources
                ? `Found ${research.sources} source${research.sources === 1 ? "" : "s"}${research.publishers.length ? `: ${research.publishers.join(", ")}` : ""}`
                : "Nothing citable found; your own material carries it"
              : undefined,
          },
          { text: "Checking each quote against its page", state: found ? "done" : s < 14 ? "next" : "now" },
          { text: "Writing the storyline, one claim per slide", state: found ? "now" : "next" },
          { text: "Tying every number to you or a source", state: "next" },
        ];
  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-8 px-4 py-16 sm:px-8 sm:py-24">
      <div className="flex items-baseline justify-between gap-6">
        <p className="font-display text-[26px] leading-tight sm:text-[30px]">
          {status === "brief" ? "Reading your brief" : "Writing your outline"}
        </p>
        <span className="font-mono text-[13px] text-ink-2 tabular-nums" aria-label="Time so far">
          {clock(s)}
        </span>
      </div>
      <ol className="flex flex-col border-t border-rule" aria-live="polite">
        {steps.map((step) => (
          <li key={step.text} className="flex gap-4 border-b border-rule py-3.5">
            <Mark state={step.state} />
            <div className="min-w-0">
              <p className={cn("text-[15px] transition-colors duration-500", step.state === "next" ? "text-ink-2/55" : "text-ink")}>
                {step.text}
              </p>
              {step.detail && <p className="mt-0.5 animate-[settle_420ms_ease-out] text-[13px] text-ink-2">{step.detail}</p>}
              {step.state === "now" && (
                <div aria-hidden="true" className="mt-2 h-px w-40 overflow-hidden bg-rule">
                  <div className="h-px w-1/3 animate-[sweep_1.6s_ease-in-out_infinite] bg-ink" />
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>
      <p className="text-sm text-ink-2">
        {status === "brief" ? "Usually under half a minute." : "Usually about a minute."} You can leave this page; nothing is lost.
      </p>
    </main>
  );
}

function Mark({ state }: { state: State }) {
  return (
    <span aria-label={state === "done" ? "Done" : state === "now" ? "Working on it" : "Next"} className="mt-1 grid size-4 shrink-0 place-content-center">
      {state === "done" ? (
        <svg viewBox="0 0 16 16" className="size-4 animate-[settle_300ms_ease-out] text-accent" aria-hidden="true">
          <circle cx="8" cy="8" r="8" fill="currentColor" />
          <path d="M4.5 8.2l2.3 2.3 4.7-4.9" fill="none" stroke="var(--color-paper)" strokeWidth="1.6" />
        </svg>
      ) : state === "now" ? (
        <span className="size-3.5 animate-spin rounded-full border-[1.5px] border-rule border-t-ink" />
      ) : (
        <span className="size-3 rounded-full border border-rule" />
      )}
    </span>
  );
}

// The build's live feed: the last few things the studio did, newest first.
export function Feed({ events, outline }: { events: LiveEvent[]; outline: LiveDeck["outline"] }) {
  const number = (id: string | null) => outline.findIndex((p) => p.id === id) + 1;
  const lines = events
    .map((e) => ({ seq: e.seq, text: describe(e, number(e.slideId)) }))
    .filter((l): l is { seq: number; text: string } => l.text !== null)
    .slice(-5)
    .reverse();
  if (lines.length === 0) return null;
  return (
    <ol aria-live="polite" className="flex flex-col gap-1">
      {lines.map((l, i) => (
        <li
          key={l.seq}
          className={cn(
            "flex animate-[settle_420ms_ease-out] items-baseline gap-2 text-[13px]",
            i === 0 ? "text-ink" : "text-ink-2/70",
          )}
        >
          <span aria-hidden="true" className={cn("size-1.5 shrink-0 translate-y-[-1px] rounded-full", i === 0 ? "bg-accent" : "bg-rule")} />
          {l.text}
        </li>
      ))}
    </ol>
  );
}

function describe(e: LiveEvent, n: number): string | null {
  if (e.type === "stage" && e.name === "direction") {
    return e.state === "started" ? "The art director is planning the whole deck" : "Art direction set: every slide has its idea";
  }
  if (e.type === "stage" && e.name === "review") {
    return e.state === "started" ? "The design director is reviewing the deck as one piece" : "Review done";
  }
  if (e.type === "slide_step" && n > 0) {
    if (e.step === "design") return `Designing slide ${n}`;
    if (e.step === "improve") return `Looking at slide ${n} rendered, and redesigning what's weak`;
    if (e.step === "repair") return `Slide ${n} didn't measure clean: repairing it`;
  }
  if (e.type === "slide_ready" && n > 0) {
    return e.status === "passed" ? `Slide ${n} checked in the browser: passed` : `Slide ${n} checked: needs your eye`;
  }
  return null;
}

// Which slides are being worked on now, and at what step.
export function liveSteps(events: LiveEvent[]): Record<string, string> {
  const at: Record<string, string> = {};
  for (const e of events) {
    if (e.type === "slide_step" && e.slideId && e.step) at[e.slideId] = e.step;
    if (e.type === "slide_ready" && e.slideId) delete at[e.slideId];
  }
  return at;
}
