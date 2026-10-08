"use client";

// A live deck (phase 27): one screen that follows the deck through its real
// states — questions, the outline gate, the watch, the finished deck — reading
// the API and its event stream. Only real states are shown; nothing is
// invented or delayed (docs/v4/ui-research.md -> the ethics line).
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { LiveEditor } from "@/components/live-editor";
import { OutlineGate, type Decisions } from "@/components/outline-gate";
import { SlideThumb } from "@/components/slide-thumb";
import { StyleCard } from "@/components/style-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { api, parseEvent, type LiveDeck as Deck, type LiveEvent, type Notice } from "@/lib/api/client";

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
  if (wait) return <Waiting text={wait} />;
  if (deck.status === "error") return <Problem text={deck.error || "Something went wrong on our side."} />;
  if (deck.status === "interview") return <Questions deck={deck} onDone={refresh} />;
  if (deck.status === "approve") {
    return (
      <OutlineGate
        deck={{ ...deck, questions: [] }}
        style={<StyleCard deckId={deck.id} />}
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
    );
  }
  return <Building deck={deck} ready={ready} notice={notice} onChange={refresh} />;
}

function Waiting({ text }: { text: string }) {
  return (
    <main className="grid min-h-[60dvh] place-content-center px-8">
      <p className="font-display text-2xl" aria-live="polite">
        {text}
      </p>
    </main>
  );
}

function Problem({ text }: { text: string }) {
  return (
    <main className="mx-auto max-w-xl px-8 py-16">
      <Alert variant="destructive">
        <AlertTitle>This deck stopped</AlertTitle>
        <AlertDescription>{text}</AlertDescription>
      </Alert>
      <Button asChild variant="link" className="mt-4 px-0">
        <Link href="/">Start again</Link>
      </Button>
    </main>
  );
}

function Questions({ deck, onDone }: { deck: Deck; onDone: () => void }) {
  const [answers, setAnswers] = useState<string[]>(deck.questions.map(() => ""));
  const [busy, setBusy] = useState(false);
  const send = async (skip: boolean) => {
    setBusy(true);
    await api.answer(deck.id, answers, skip);
    onDone();
  };
  return (
    <main className="mx-auto grid max-w-2xl gap-8 px-8 py-10">
      <h1 className="font-display text-3xl">A few questions, so it says what you mean</h1>
      {deck.questions.map((q, i) => (
        <fieldset key={q.question} className="grid gap-3">
          <legend className="mb-2 font-display text-xl">{q.question}</legend>
          <div className="flex flex-wrap gap-2">
            {q.suggestions.map((s) => (
              <Button
                key={s}
                type="button"
                variant={answers[i] === s ? "default" : "outline"}
                className="h-auto py-2 text-left whitespace-normal"
                onClick={() => setAnswers((a) => a.map((v, j) => (j === i ? s : v)))}
              >
                {s}
              </Button>
            ))}
          </div>
          <input
            aria-label="Or in your own words"
            placeholder="Or in your own words"
            value={q.suggestions.includes(answers[i] ?? "") ? "" : (answers[i] ?? "")}
            onChange={(e) => setAnswers((a) => a.map((v, j) => (j === i ? e.target.value : v)))}
            className="border-b border-ink bg-transparent py-2 outline-none"
          />
        </fieldset>
      ))}
      <div className="flex items-center gap-4">
        <Button size="lg" disabled={busy} onClick={() => void send(false)}>
          Write my outline
        </Button>
        <Button variant="link" disabled={busy} className="px-0 text-muted-foreground" onClick={() => void send(true)}>
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
  const [editing, setEditing] = useState(false);
  // Finished slides come from the deck as well as the stream, so a reload or a
  // resumed build shows what is already done.
  const done = { ...Object.fromEntries(deck.slides.map((s) => [s.id, s.status])), ...ready };
  const count = deck.outline.filter((p) => done[p.id]).length;
  const total = deck.outline.length;
  const finished = deck.status === "ready";
  const stopped = deck.status === "aborted";
  return (
    <main className="px-8 py-8">
      <div className="mb-6 flex items-end justify-between gap-6">
        <div aria-live="polite">
          <h1 className="font-display text-3xl">
            {finished ? "Your deck is ready" : stopped ? "Stopped" : `Composing your deck — ${count} of ${total} done`}
          </h1>
          <p className="mt-1 text-sm text-ink-2">
            {finished
              ? "Every slide was composed and checked in a browser."
              : stopped
                ? `${count} finished slides are kept. Continue picks up where it stopped, without paying for them again.`
                : "Each slide appears once it has been composed and checked. You can leave this page; nothing is lost."}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {finished ? (
            <>
              <Button variant={editing ? "default" : "outline"} size="lg" onClick={() => setEditing((v) => !v)}>
                {editing ? "Done editing" : "Edit"}
              </Button>
              <Button asChild size="lg">
                <a href={api.exportUrl(deck.id, "present")} target="_blank" rel="noreferrer">
                  Present
                </a>
              </Button>
              <Button asChild variant="outline" size="lg">
                <a href={api.exportUrl(deck.id, "send")} download="deck.html">
                  Download to send
                </a>
              </Button>
              <Button asChild variant="ghost" size="lg">
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
            <Button variant="outline" size="lg" onClick={() => void api.abort(deck.id).then(onChange)}>
              Stop
            </Button>
          )}
        </div>
      </div>
      {editing && finished ? (
        <LiveEditor deck={deck} notice={notice} onChange={onChange} />
      ) : (
      <ol className="grid grid-cols-2 gap-5 md:grid-cols-4">
        {deck.outline.map((plan, i) => {
          const status = done[plan.id];
          const headline = plan.fields.find((f) => f.name === "headline")?.text ?? "";
          return (
            <li key={plan.id} className="grid gap-2">
              {status ? (
                <div className="animate-[settle_420ms_ease-out]">
                  <SlideThumb src={api.thumb(deck.id, plan.id, deck.version)} alt={`Slide ${i + 1}: ${headline}`} />
                </div>
              ) : (
                <div className="grid aspect-video content-end border border-dashed border-rule bg-paper-2 p-3">
                  <p className="line-clamp-3 font-display text-sm leading-snug text-ink-2">{headline}</p>
                </div>
              )}
              <p className="flex justify-between text-xs text-ink-2">
                <span>{i + 1}</span>
                <span>{status ? (status === "passed" ? "Checked" : "Needs attention") : stopped ? "Not started" : "Composing"}</span>
              </p>
            </li>
          );
        })}
      </ol>
      )}
    </main>
  );
}
