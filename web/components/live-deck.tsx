"use client";

// A live deck (phase 27): one screen that follows the deck through its real
// states — questions, the outline gate, the watch, the finished deck — reading
// the API and its event stream. Only real states are shown; nothing is
// invented or delayed (docs/v4/ui-research.md -> the ethics line).
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { LiveEditor } from "@/components/live-editor";
import { Placard } from "@/components/placard";
import { OutlineGate, type Decisions } from "@/components/outline-gate";
import { SlideThumb } from "@/components/slide-thumb";
import { LogoPicker } from "@/components/logo-picker";
import { StyleCard } from "@/components/style-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { api, parseEvent, type LiveDeck as Deck, type LiveEvent, type Notice } from "@/lib/api/client";
import { cn } from "@/lib/utils";

const WAITING: Partial<Record<Deck["status"], string>> = {
  brief: "Reading your brief and writing a few questions…",
  outline: "Finding sources and writing your outline…",
};

// ~30 lines instead of EventSource, which cannot send the token phase 29 needs.
async function follow(id: string, after: number, onEvent: (e: LiveEvent) => void, signal: AbortSignal) {
  const res = await fetch(`/api/decks/${id}/events`, { headers: { "Last-Event-ID": String(after) }, signal });
  if (!res.body) return;
  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += value;
    let cut = buffer.indexOf("\n\n");
    while (cut >= 0) {
      const block = buffer.slice(0, cut);
      buffer = buffer.slice(cut + 2);
      const data = block.split("\n").find((l) => l.startsWith("data: "));
      const event = data ? parseEvent(data.slice(6)) : null;
      if (event) onEvent(event);
      cut = buffer.indexOf("\n\n");
    }
  }
}

export function LiveDeck({ id }: { id: string }) {
  const [deck, setDeck] = useState<Deck | null>(null);
  const [problem, setProblem] = useState<string | null>(null);
  const [ready, setReady] = useState<Record<string, string>>({}); // slide id -> status
  const [notice, setNotice] = useState<Notice | null>(null); // the editor's last outcome
  const seen = useRef(0);

  const refresh = useCallback(async () => {
    const got = await api.read(id);
    if (got.ok) setDeck(got.value);
    else setProblem(got.error);
  }, [id]);

  useEffect(() => {
    // Mount: read once, then follow events; reconnect from the last seen seq.
    const stop = new AbortController();
    const loop = async () => {
      await refresh();
      while (!stop.signal.aborted) {
        try {
          await follow(
            id,
            seen.current,
            (e) => {
              seen.current = e.seq;
              if (e.type === "slide_ready" && e.slideId) {
                const sid = e.slideId;
                setReady((m) => ({ ...m, [sid]: e.status ?? "passed" }));
              }
              if (e.type === "proposal_ready" && e.slideId) {
                setNotice({ text: "Your change is ready. Compare it, then keep it or not.", seq: e.seq, proposal: e.slideId });
              }
              if (e.type === "edit_done" || e.type === "edit_refused") {
                const text = e.type === "edit_refused" ? (e.message ?? "That change was not made.") : "Saved and checked.";
                setNotice({ text, seq: e.seq });
              }
              if (["questions_ready", "outline_ready", "done", "error", "stage", "edit_done", "edit_refused"].includes(e.type)) {
                void refresh();
              }
            },
            stop.signal,
          );
        } catch {
          if (stop.signal.aborted) return;
        }
        await new Promise((r) => setTimeout(r, 1500)); // the stream ended or dropped: resume
        void refresh();
      }
    };
    void loop();
    return () => stop.abort();
  }, [id, refresh]);

  if (problem && !deck) return <Problem text={problem} />;
  if (!deck) return <Waiting text="Opening your deck…" />;

  const wait = WAITING[deck.status];
  if (wait) {
    return (
      <>
        <DeckHeader deck={deck} />
        <Waiting text={wait} />
      </>
    );
  }
  if (deck.status === "error") {
    return (
      <>
        <DeckHeader deck={deck} />
        <Problem
          text={deck.error || "Something went wrong on our side."}
          onRetry={async () => {
            const again = await api.retry(deck.id);
            if (again.ok) setDeck(again.value);
            else setProblem(again.error);
          }}
        />
      </>
    );
  }
  if (deck.status === "interview") {
    return (
      <>
        <DeckHeader deck={deck} />
        <Questions deck={deck} onDone={refresh} />
      </>
    );
  }
  if (deck.status === "approve") {
    return (
      <>
        <DeckHeader deck={deck} />
        <OutlineGate
          deck={{ ...deck, questions: [] }}
          thesis={false}
          style={
            <>
              <StyleCard deckId={deck.id} />
              <LogoPicker deck={deck} onChange={refresh} />
            </>
          }
          onApprove={async (decided: Decisions, order: string[]) => {
            const decisions = Object.fromEntries(
              Object.entries(decided).map(([k, v]) => [k, v === "cut" ? ("rejected" as const) : ("approved" as const)]),
            );
            const saved = await api.decide(deck.id, deck.version, decisions, order);
            if (!saved.ok) return setProblem(saved.error);
            const started = await api.build(deck.id);
            if (!started.ok) return setProblem(started.error);
            setDeck(started.value.status === "approve" ? { ...started.value, status: "building" } : started.value);
          }}
        />
      </>
    );
  }
  return <Building deck={deck} ready={ready} notice={notice} onChange={refresh} />;
}

// The path a deck takes, with where this one stands (docs/v4/ui-research.md ->
// goal gradient). Real states only.
const STEPS = ["Questions", "Outline", "Build", "Send"] as const;

function stepOf(deck: Deck): number {
  const { status } = deck;
  if (status === "brief" || status === "interview") return 0;
  if (status === "outline" || status === "approve") return 1;
  if (status === "ready") return 3;
  // A stopped deck shows the step it stopped in.
  if (status === "error") return deck.outline.length > 0 ? 2 : deck.questions.length > 0 ? 1 : 0;
  return 2;
}

function DeckHeader({
  deck,
  actions,
  line,
  compact = false,
}: {
  deck: Deck;
  actions?: React.ReactNode;
  line?: React.ReactNode;
  compact?: boolean; // the editor needs the room: one line of title, no status
}) {
  const at = stepOf(deck);
  return (
    <div className="border-b border-rule">
      <div
        className={cn(
          "mx-auto flex max-w-[1440px] flex-col gap-5 px-4 sm:px-8 lg:flex-row lg:items-end lg:gap-10",
          compact ? "py-4" : "py-6",
        )}
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
            <Link href="/decks" className="placard hover:text-ink">
              ← Your decks
            </Link>
            <ol aria-label="Steps" className="flex items-center gap-2 placard">
              {STEPS.map((s, i) => (
                <li key={s} className="flex items-center gap-2">
                  {i > 0 && <span aria-hidden="true" className="h-px w-3 bg-rule sm:w-5" />}
                  <span
                    aria-current={i === at ? "step" : undefined}
                    className={cn(i === at ? "text-ink" : i < at ? "text-ink-2" : "text-ink-2/50")}
                  >
                    {s}
                  </span>
                </li>
              ))}
            </ol>
          </div>
          <h1
            className={cn(
              "mt-3 max-w-4xl font-display leading-[1.15] tracking-[-0.015em] text-balance",
              compact ? "truncate text-[20px]" : "line-clamp-3 text-[24px] sm:text-[30px]",
            )}
          >
            {deck.thesis || deck.prompt || "Your deck"}
          </h1>
          {line && !compact && (
            <div className="mt-2 text-sm text-ink-2" aria-live="polite">
              {line}
            </div>
          )}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}

function Waiting({ text }: { text: string }) {
  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-24 sm:px-8">
      <p className="font-display text-[28px] leading-tight" aria-live="polite">
        {text}
      </p>
      <div aria-hidden="true" className="h-px w-full overflow-hidden bg-rule">
        <div className="h-px w-1/3 animate-[sweep_1.8s_ease-in-out_infinite] bg-ink" />
      </div>
      <p className="text-sm text-ink-2">This takes about a minute. You can leave this page; nothing is lost.</p>
    </main>
  );
}

function Problem({ text, onRetry }: { text: string; onRetry?: () => Promise<void> }) {
  const [busy, setBusy] = useState(false);
  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-5 px-4 py-16 sm:px-8">
      <Alert variant="destructive">
        <AlertTitle>This deck stopped</AlertTitle>
        <AlertDescription>
          {text} Your brief and answers are kept, so trying again picks up from the step that failed.
        </AlertDescription>
      </Alert>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        {onRetry && (
          <Button
            disabled={busy}
            onClick={() => {
              setBusy(true);
              void onRetry().finally(() => setBusy(false));
            }}
          >
            {busy ? "Trying again…" : "Try again"}
          </Button>
        )}
        <Button asChild variant="link" className="px-0 text-ink-2">
          <Link href="/">Start a new deck</Link>
        </Button>
      </div>
    </main>
  );
}

// The proof question's third suggestion names a kind of proof; picking it asks
// for the proof itself, never sends the suggestion as if it were proof.
const NO_PROOF = ["none yet", "search the web"];
const asksPaste = (q: Deck["questions"][number], s: string) =>
  q.fills === "proof" && !NO_PROOF.includes(s.toLowerCase());

function Questions({ deck, onDone }: { deck: Deck; onDone: () => void }) {
  const [answers, setAnswers] = useState<string[]>(deck.questions.map(() => ""));
  const [picked, setPicked] = useState<(string | null)[]>(deck.questions.map(() => null));
  const [busy, setBusy] = useState(false);
  const send = async (skip: boolean) => {
    setBusy(true);
    await api.answer(deck.id, answers, skip);
    onDone();
  };
  const set = (i: number, value: string) => setAnswers((a) => a.map((v, j) => (j === i ? value : v)));
  const pick = (i: number, s: string | null) => setPicked((p) => p.map((v, j) => (j === i ? s : v)));
  return (
    <main className="mx-auto max-w-2xl px-4 py-10 sm:px-8">
      <h2 className="font-display text-[28px] leading-tight">A few questions, so it says what you mean</h2>
      <p className="mt-2 text-sm text-ink-2">Pick an answer or write your own. Any of them can be skipped.</p>
      <ol className="mt-8 border-t border-rule">
        {deck.questions.map((q, i) => {
          const chip = picked[i] ?? null;
          const paste = chip !== null && asksPaste(q, chip);
          // The product question has no suggestions: only the speaker knows what it does.
          const long = q.fills === "product" || paste;
          return (
            <li key={q.question} className="border-b border-rule py-7">
              <fieldset className="flex flex-col gap-4">
                <legend className="flex gap-4 font-display text-[22px] leading-snug">
                  <span className="text-ink-2 tabular-nums">{i + 1}</span>
                  <span>{q.question}</span>
                </legend>
                {q.suggestions.length > 0 && (
                  <div className="flex flex-wrap gap-2 sm:pl-8">
                    {q.suggestions.map((s) => (
                      <Button
                        key={s}
                        type="button"
                        variant="outline"
                        aria-pressed={chip === s}
                        className="h-auto py-2 text-left whitespace-normal aria-pressed:border-ink aria-pressed:bg-paper-2"
                        onClick={() => {
                          const off = chip === s;
                          pick(i, off ? null : s);
                          set(i, off || asksPaste(q, s) ? "" : s);
                        }}
                      >
                        {chip === s && <span aria-hidden="true">✓</span>}
                        {s}
                      </Button>
                    ))}
                  </div>
                )}
                {long ? (
                  <textarea
                    aria-label={paste ? "Paste your proof" : "In your own words"}
                    placeholder={
                      paste
                        ? "Paste it here: numbers, quotes, customer names. Leave empty if you have none yet."
                        : "What it does, who it is for, and its two or three main features"
                    }
                    rows={4}
                    value={answers[i] ?? ""}
                    onChange={(e) => set(i, e.target.value)}
                    className="resize-y border border-rule bg-transparent px-3 py-2.5 outline-none placeholder:text-ink-2/70 focus:border-ink sm:ml-8"
                  />
                ) : (
                  <input
                    aria-label="Or in your own words"
                    placeholder="Or in your own words"
                    value={chip !== null ? "" : (answers[i] ?? "")}
                    onChange={(e) => {
                      pick(i, null);
                      set(i, e.target.value);
                    }}
                    className="border-b border-rule bg-transparent py-2 outline-none placeholder:text-ink-2/70 focus:border-ink sm:ml-8"
                  />
                )}
              </fieldset>
            </li>
          );
        })}
      </ol>
      <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
        <Button size="lg" disabled={busy} onClick={() => void send(false)}>
          Write my outline
        </Button>
        <Button variant="link" disabled={busy} className="px-0 text-ink-2" onClick={() => void send(true)}>
          Skip — use what I gave you
        </Button>
      </div>
    </main>
  );
}

function Building({
  deck,
  ready,
  notice,
  onChange,
}: {
  deck: Deck;
  ready: Record<string, string>;
  notice: Notice | null;
  onChange: () => void;
}) {
  const [editing, setEditing] = useState<string | null>(null); // the slide the editor opens on
  // Finished slides come from the deck as well as the stream, so a reload or a
  // resumed build shows what is already done.
  const done = { ...Object.fromEntries(deck.slides.map((s) => [s.id, s.status])), ...ready };
  const count = deck.outline.filter((p) => done[p.id]).length;
  const total = deck.outline.length;
  const finished = deck.status === "ready";
  const stopped = deck.status === "aborted";
  // Named before anything is downloaded, never hidden (phase 32).
  const flagged = deck.outline.flatMap((p, i) => (done[p.id] && done[p.id] !== "passed" ? [i + 1] : []));
  const first = deck.outline[0]?.id ?? "";

  const actions = finished ? (
    <>
      <Button
        variant="outline"
        className="hidden lg:inline-flex"
        onClick={() => setEditing((v) => (v === null ? first : null))}
      >
        {editing !== null ? "Done editing" : "Edit"}
      </Button>
      <Button asChild variant="outline">
        <a href={api.exportUrl(deck.id, "present")} target="_blank" rel="noreferrer">
          Present
        </a>
      </Button>
      <Button asChild>
        <a href={api.exportUrl(deck.id, "send")} download="deck.html">
          Download to send
        </a>
      </Button>
      <Button asChild variant="ghost">
        <a href={api.exportUrl(deck.id, "pdf")} download="deck.pdf">
          PDF
        </a>
      </Button>
    </>
  ) : stopped ? (
    <Button size="lg" onClick={() => void api.build(deck.id).then(onChange)}>
      Continue
    </Button>
  ) : (
    <Button variant="outline" onClick={() => void api.abort(deck.id).then(onChange)}>
      Stop
    </Button>
  );
  const line = finished
    ? `${total} slides, every one checked in a browser. Present opens it with your notes; the download is the slides only.`
    : stopped
      ? `Stopped with ${count} of ${total} slides done. Continue picks up where it stopped, without paying for them again.`
      : `Composing your deck — ${count} of ${total} done. You can leave this page; nothing is lost.`;

  return (
    <>
      <DeckHeader deck={deck} actions={actions} line={line} compact={editing !== null && finished} />
      {!finished && (
        <div aria-hidden="true" className="h-0.5 bg-rule">
          <div className="h-0.5 bg-ink transition-[width] duration-500" style={{ width: `${(count / Math.max(total, 1)) * 100}%` }} />
        </div>
      )}
      {editing !== null && finished ? (
        <LiveEditor deck={deck} notice={notice} onChange={onChange} start={editing} />
      ) : (
        <main className="mx-auto max-w-[1440px] px-4 py-8 sm:px-8">
          {finished && flagged.length > 0 && (
            <Alert className="mb-8 border-flag/40">
              <AlertTitle>
                {flagged.length === 1 ? "One slide needs" : `${flagged.length} slides need`} your eye before you send it
              </AlertTitle>
              <AlertDescription>
                {flagged.map((n) => `Slide ${n}`).join(", ")}: something on {flagged.length === 1 ? "it" : "them"} didn&apos;t pass
                the check in the browser, usually words too long for their place. Open it, then Fit to slide or shorten the
                words.
              </AlertDescription>
            </Alert>
          )}
          <ol className="grid gap-x-6 gap-y-9 sm:grid-cols-2 lg:grid-cols-3">
            {deck.outline.map((plan, i) => {
              const status = done[plan.id];
              const headline = plan.fields.find((f) => f.name === "headline")?.text ?? "";
              const note = status
                ? status === "passed"
                  ? undefined
                  : "Needs attention"
                : stopped
                  ? "Not started"
                  : "Composing…";
              return (
                <li key={plan.id}>
                  {status ? (
                    <button
                      type="button"
                      disabled={!finished}
                      onClick={() => setEditing(plan.id)}
                      className="block w-full animate-[settle_420ms_ease-out] text-left enabled:cursor-pointer lg:enabled:hover:opacity-90"
                      aria-label={finished ? `Edit slide ${i + 1}` : undefined}
                    >
                      <SlideThumb src={api.thumb(deck.id, plan.id, deck.version)} alt={`Slide ${i + 1}: ${headline}`} />
                    </button>
                  ) : (
                    <div className="flex aspect-video flex-col justify-end border border-dashed border-rule bg-paper-2/60 p-4">
                      <p className="line-clamp-3 font-display text-base leading-snug text-ink-2">{headline}</p>
                    </div>
                  )}
                  <Placard
                    lead={String(i + 1).padStart(2, "0")}
                    label={plan.beat || plan.intent}
                    aside={note}
                    flag={!!status && status !== "passed"}
                  />
                </li>
              );
            })}
          </ol>
        </main>
      )}
    </>
  );
}
