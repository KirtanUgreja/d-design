"use client";

// The generation watch (docs/design/app.md § 4; docs/v4/plan/32-watch-reveal.md):
// the outline as ghost slots, each filled the moment its slide was really
// final — the recorded events replayed at their real times. Only real states;
// no invented steps, no added delay (docs/v4/ui-research.md -> the ethics line).
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { SlideThumb } from "@/components/slide-thumb";
import type { Recording } from "@/lib/fixtures";
import { Button } from "@/components/ui/button";

type SlotState = { kind: "composing" } | { kind: "ready"; flagged: boolean };

export function Watch({ deck }: { deck: Recording }) {
  const ready = useMemo(
    () => deck.events.filter((e) => e.type === "slide_ready" && e.slideId).sort((a, b) => a.t - b.t),
    [deck.events],
  );
  const doneAt = deck.events.find((e) => e.type === "done")?.t ?? ready.at(-1)?.t ?? 0;
  const thumbs = useMemo(() => new Map(deck.slides.map((s) => [s.id, s.thumb])), [deck.slides]);
  const [slots, setSlots] = useState<Record<string, SlotState>>({});
  const [elapsed, setElapsed] = useState(0);
  const [running, setRunning] = useState(true);
  const timers = useRef<number[]>([]);
  const clock = useRef({ startedAt: 0, offset: 0 });

  const schedule = useCallback(
    (from: number) => {
      clock.current = { startedAt: performance.now(), offset: from };
      for (const e of ready) {
        if (e.t < from || !e.slideId) continue;
        const id = e.slideId;
        timers.current.push(
          window.setTimeout(
            () => setSlots((m) => ({ ...m, [id]: { kind: "ready", flagged: e.status !== "passed" } })),
            (e.t - from) * 1000,
          ),
        );
      }
      timers.current.push(window.setTimeout(() => setRunning(false), (doneAt - from) * 1000));
    },
    [ready, doneAt],
  );

  const stop = () => {
    for (const t of timers.current) window.clearTimeout(t);
    timers.current = [];
  };

  useEffect(() => {
    schedule(0);
    return stop;
  }, [schedule]);

  useEffect(() => {
    if (!running) return;
    const tick = window.setInterval(() => {
      const { startedAt, offset } = clock.current;
      setElapsed(offset + (performance.now() - startedAt) / 1000);
    }, 250);
    return () => window.clearInterval(tick);
  }, [running]);

  const doneCount = Object.values(slots).filter((s) => s.kind === "ready").length;
  const total = deck.outline.length;
  const finished = doneCount === total;
  const aborted = !running && !finished;

  return (
    <main className="px-8 py-8">
      <div className="mb-6 flex items-end justify-between gap-6">
        <div aria-live="polite">
          <h1 className="font-display text-3xl">
            {finished ? "Your deck is ready" : aborted ? "Stopped" : `Composing your deck — ${doneCount} of ${total} done`}
          </h1>
          <p className="mt-1 text-sm text-ink-2">
            {finished
              ? `Every slide was composed and checked in a browser, in ${Math.round(doneAt)} seconds.`
              : aborted
                ? `${doneCount} finished slides are kept. Continue picks up where it stopped.`
                : "Each slide appears once it has been composed and checked. You can leave this page; nothing is lost."}
          </p>
        </div>
        <div className="flex items-center gap-4">
          <span className="font-mono text-sm tabular-nums text-ink-2">{Math.floor(elapsed)}s</span>
          {finished ? (
            <Button asChild size="lg">
              <Link href={`/deck/${deck.id}/edit`}>Open your deck</Link>
            </Button>
          ) : aborted ? (
            <Button
              size="lg"
              onClick={() => {
                setRunning(true);
                schedule(elapsed);
              }}
            >
              Continue
            </Button>
          ) : (
            <Button
              variant="outline"
              size="lg"
              onClick={() => {
                stop();
                setRunning(false);
              }}
            >
              Stop
            </Button>
          )}
        </div>
      </div>
      <ol className="grid grid-cols-2 gap-5 md:grid-cols-4">
        {deck.outline.map((plan, i) => {
          const state = slots[plan.id] ?? { kind: "composing" as const };
          const headline = plan.fields.find((f) => f.name === "headline")?.text ?? "";
          const thumb = thumbs.get(plan.id);
          return (
            <li key={plan.id} className="grid gap-2">
              {state.kind === "ready" && thumb ? (
                <div className="animate-[settle_420ms_ease-out]">
                  <SlideThumb src={`/fixtures/${deck.id}/${thumb}`} alt={`Slide ${i + 1}: ${headline}`} />
                </div>
              ) : (
                <div className="grid aspect-video content-end border border-dashed border-rule bg-paper-2 p-3">
                  <p className="line-clamp-3 font-display text-sm leading-snug text-ink-2">{headline}</p>
                </div>
              )}
              <p className="flex justify-between text-xs text-ink-2">
                <span>{i + 1}</span>
                <span>
                  {state.kind === "ready" ? (state.flagged ? "Needs attention" : "Checked") : aborted ? "Not started" : "Composing"}
                </span>
              </p>
            </li>
          );
        })}
      </ol>
      {!finished && <p className="mt-8 text-sm text-ink-2">When it is done: click any slide in the editor to change its words.</p>}
    </main>
  );
}
