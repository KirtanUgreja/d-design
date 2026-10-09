"use client";

// The editor for a live deck (docs/v4/plan/28-editor.md): change words, move
// or delete slides, fit a slide its new words broke, ask for a change in
// words, try new colours — each a job the worker checks in a browser before
// it is saved, each a labelled version undo returns to. No HTML, no free
// colour picker: the look is the unit of style (docs/design/app.md -> "The
// colour picker that does not exist").
//
// Three columns: the filmstrip, the slide on its wall (it stays in view while
// the inspector scrolls), and the inspector — this slide, or the whole deck.
import { useEffect, useState } from "react";

import { SlideThumb } from "@/components/slide-thumb";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { api, type History, type LiveDeck, type Notice } from "@/lib/api/client";
import { cn } from "@/lib/utils";

const NAMES: Record<string, string> = {
  headline: "Headline",
  kicker: "Kicker",
  stat: "Number",
  "stat-label": "What the number means",
  source: "Source",
};
const label = (name: string) => NAMES[name] ?? (name.startsWith("point-") ? `Point ${name.slice(6)}` : name);

export function LiveEditor({
  deck,
  notice,
  onChange,
  start,
}: {
  deck: LiveDeck;
  notice: Notice | null;
  onChange: () => void;
  start?: string; // the slide to open on
}) {
  const [selected, setSelected] = useState(start ?? deck.outline[0]?.id ?? "");
  // In flight until the deck's version or the latest notice moves on: then the job landed.
  const [pending, setPending] = useState<{ what: string; version: number; seq: number } | null>(null);
  const busy =
    pending && pending.version === deck.version && pending.seq === (notice?.seq ?? 0) ? pending.what : null;
  const [problem, setProblem] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState(0); // the seq of a proposal set aside
  const [history, setHistory] = useState<History>({ labels: [], at: -1 });
  const plan = deck.outline.find((p) => p.id === selected) ?? deck.outline[0];
  const index = deck.outline.findIndex((p) => p.id === plan?.id);
  const status = deck.slides.find((s) => s.id === plan?.id)?.status ?? "";
  const ends = new Set([deck.outline[0]?.id, deck.outline.at(-1)?.id]);

  useEffect(() => {
    // The deck's version moves with every saved change, undo included.
    let live = true;
    void api.history(deck.id).then((h) => {
      if (live && h.ok) setHistory(h.value);
    });
    return () => {
      live = false;
    };
  }, [deck.id, deck.version]);

  const run = async (what: string, change: () => Promise<{ ok: boolean; error?: string }>) => {
    setProblem(null);
    setPending({ what, version: deck.version, seq: notice?.seq ?? 0 });
    const done = await change();
    if (!done.ok) {
      setPending(null);
      setProblem(done.error ?? "That didn't work. Try again.");
    }
  };

  const move = (by: number) => {
    const ids = deck.outline.map((p) => p.id);
    const to = index + by;
    if (to < 1 || to > ids.length - 2 || ends.has(plan?.id)) return;
    const [it] = ids.splice(index, 1);
    if (it) ids.splice(to, 0, it);
    void run("Moving the slide", () => api.reorder(deck.id, ids));
  };

  const step = async (dir: "undo" | "redo") => {
    setProblem(null);
    const moved = dir === "undo" ? await api.undo(deck.id) : await api.redo(deck.id);
    if (!moved.ok) setProblem(moved.error);
    onChange();
  };

  if (!plan) return null;
  const proposal = notice?.proposal === plan.id && dismissed !== notice.seq && !busy ? notice : null;
  const canUndo = history.at > 0 && !busy;
  const canRedo = history.at < history.labels.length - 1 && !busy;

  return (
    <div className="mx-auto grid max-w-[1440px] gap-6 px-4 py-6 sm:px-8 lg:grid-cols-[112px_minmax(0,1fr)_360px] lg:gap-8">
      <nav
        aria-label="Slides"
        className="flex gap-3 overflow-x-auto pb-2 lg:sticky lg:top-[72px] lg:max-h-[calc(100dvh-88px)] lg:flex-col lg:self-start lg:overflow-x-hidden lg:overflow-y-auto lg:pr-1 lg:pb-0"
      >
        {deck.outline.map((p, i) => (
          <button
            key={p.id}
            type="button"
            onClick={() => setSelected(p.id)}
            aria-current={p.id === plan.id}
            aria-label={`Slide ${i + 1}`}
            className="group w-28 shrink-0 text-left lg:w-full"
          >
            <SlideThumb
              src={api.thumb(deck.id, p.id, deck.version)}
              alt=""
              className={cn(
                "transition-[outline-color]",
                p.id === plan.id ? "outline-2 outline-offset-2 outline-ink" : "group-hover:outline group-hover:outline-rule",
              )}
            />
            <span className={cn("mt-1 block placard", p.id === plan.id && "text-ink")}>
              {String(i + 1).padStart(2, "0")}
              {deck.slides.find((s) => s.id === p.id)?.status === "flagged" ? " · !" : ""}
            </span>
          </button>
        ))}
      </nav>

      <section aria-label="The slide" className="flex min-w-0 flex-col gap-3 lg:sticky lg:top-[72px] lg:self-start">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="placard">
            Slide {index + 1} of {deck.outline.length}
            {plan.beat ? ` · ${plan.beat}` : ""}
          </p>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              disabled={!canUndo}
              title={canUndo ? `Undo: ${history.labels[history.at]}` : undefined}
              onClick={() => void step("undo")}
            >
              Undo
            </Button>
            <Button variant="ghost" size="sm" disabled={!canRedo} onClick={() => void step("redo")}>
              Redo
            </Button>
          </div>
        </div>
        <div className="bg-paper-2 p-3 sm:p-6">
          <SlideThumb src={api.thumb(deck.id, plan.id, deck.version)} alt={`Slide ${index + 1}, as checked`} />
        </div>
        <div className="flex min-h-9 flex-wrap items-center gap-3 text-sm" aria-live="polite">
          {busy ? (
            <span className="text-ink-2">{busy}… checking it in a browser.</span>
          ) : status === "passed" ? (
            <span className="text-ink-2">Checked in a browser.</span>
          ) : status ? (
            <>
              <span className="text-flag">Needs attention: its words no longer fit.</span>
              <Button variant="outline" size="sm" onClick={() => void run("Fitting the slide", () => api.fit(deck.id, plan.id))}>
                Fit to slide
              </Button>
            </>
          ) : null}
        </div>
        {proposal && (
          <figure className="flex flex-col gap-3 border-t border-ink pt-4">
            <figcaption className="text-sm">
              <span className="font-medium">Your change,</span>{" "}
              <span className="text-ink-2">checked in a browser. Nothing changes until you keep it.</span>
            </figcaption>
            <div className="bg-paper-2 p-3 sm:p-6">
              <SlideThumb src={api.proposalThumb(deck.id, plan.id, proposal.seq)} alt={`Slide ${index + 1}, with your change`} />
            </div>
            <div className="flex gap-2">
              <Button onClick={() => void run("Applying your change", () => api.accept(deck.id, plan.id))}>Keep this</Button>
              <Button variant="ghost" onClick={() => setDismissed(proposal.seq)}>
                Discard
              </Button>
            </div>
          </figure>
        )}
        {(problem || (notice && !busy && !proposal)) && (
          <Alert variant={problem ? "destructive" : "default"}>
            <AlertDescription>{problem ?? notice?.text}</AlertDescription>
          </Alert>
        )}
      </section>

      <aside className="min-w-0">
        <Tabs defaultValue="slide" className="gap-6">
          <TabsList variant="line" className="w-full justify-start border-b border-rule">
            <TabsTrigger value="slide">This slide</TabsTrigger>
            <TabsTrigger value="deck">The deck</TabsTrigger>
          </TabsList>
          <TabsContent value="slide" className="flex flex-col gap-6">
            <AskBox
              key={plan.id}
              disabled={!!busy}
              onAsk={(text) => void run("Asking for a change", () => api.ask(deck.id, plan.id, text))}
            />
            <Separator />
            <div className="flex flex-col gap-4">
              <p className="placard">Words</p>
              {plan.fields
                .filter((f) => f.name !== "source")
                .map((f) => (
                  <FieldEditor
                    key={`${plan.id}-${f.name}-${deck.version}`}
                    name={label(f.name)}
                    value={f.text}
                    disabled={!!busy}
                    onSave={(text) => void run("Saving your words", () => api.editText(deck.id, plan.id, f.name, text))}
                  />
                ))}
            </div>
            {plan.notes && (
              <>
                <Separator />
                <div className="flex flex-col gap-2">
                  <p className="placard">Speaker notes</p>
                  <p className="text-sm leading-relaxed whitespace-pre-line text-ink-2">{plan.notes}</p>
                </div>
              </>
            )}
            <Separator />
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" disabled={!!busy || ends.has(plan.id) || index <= 1} onClick={() => move(-1)}>
                Move up
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={!!busy || ends.has(plan.id) || index >= deck.outline.length - 2}
                onClick={() => move(1)}
              >
                Move down
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-flag"
                disabled={!!busy || ends.has(plan.id) || deck.outline.length <= 3}
                onClick={() => void run("Deleting the slide", () => api.remove(deck.id, plan.id))}
              >
                Delete slide
              </Button>
            </div>
          </TabsContent>
          <TabsContent value="deck" className="flex flex-col gap-6">
            <DeckAsk busy={!!busy} onAsk={(text) => void run("Changing every slide", () => api.askDeck(deck.id, text))} />
            <Separator />
            <div className="flex flex-col gap-2">
              <p className="placard">Colours</p>
              <p className="text-sm text-ink-2">
                Colour and type come from the deck&apos;s look, so every slide stays one deck. A new palette keeps every
                layout.
              </p>
              <Button
                variant="outline"
                className="self-start"
                disabled={!!busy}
                onClick={() => void run("Trying new colours", () => api.recolour(deck.id))}
              >
                New colours
              </Button>
            </div>
            <Separator />
            <div className="flex flex-col gap-2">
              <p className="placard">Versions</p>
              {history.labels.length === 0 ? (
                <p className="text-sm text-ink-2">Every change you make is kept here, and undo returns to it.</p>
              ) : (
                <ol className="flex flex-col text-sm">
                  {history.labels.map((l, i) => (
                    <li
                      key={`${i}-${l}`}
                      className={cn("flex gap-3 border-b border-rule py-1.5", i === history.at ? "text-ink" : "text-ink-2")}
                    >
                      <span className="w-5 shrink-0 tabular-nums">{i + 1}</span>
                      <span className="truncate">{l}</span>
                      {i === history.at && <span className="ml-auto placard text-ink">Now</span>}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </aside>
    </div>
  );
}

// One instruction for every slide (owner, 2026-10-09): each slide is redesigned
// with it and kept where it still passes QA; one undo returns the whole deck.
function DeckAsk({ busy, onAsk }: { busy: boolean; onAsk: (text: string) => void }) {
  const [text, setText] = useState("");
  const ideas = ["Bigger, bolder headlines", "More breathing room", "Make the numbers the hero"];
  return (
    <div className="flex flex-col gap-2">
      <p className="placard">Ask for the whole deck</p>
      <p className="text-sm text-ink-2">
        Every slide is redesigned with your instruction. Layout, scale and emphasis change; your words and colours stay. A
        slide that can&apos;t take it keeps its design, and Undo returns the whole deck.
      </p>
      <textarea
        aria-label="Your instruction for every slide"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={2}
        maxLength={300}
        placeholder="e.g. bigger headlines and more space around the numbers"
        className="resize-y border border-rule bg-transparent px-3 py-2 text-sm outline-none placeholder:text-ink-2/70 focus:border-ink"
      />
      <div className="flex flex-wrap gap-1.5">
        {ideas.map((i) => (
          <Button key={i} type="button" variant="outline" size="sm" className="h-auto py-1 text-[12px]" onClick={() => setText(i)}>
            {i}
          </Button>
        ))}
      </div>
      <Button className="self-start" disabled={busy || text.trim().length < 3} onClick={() => onAsk(text.trim())}>
        {busy ? "Working on every slide…" : "Apply to every slide"}
      </Button>
    </div>
  );
}

function FieldEditor({
  name,
  value,
  disabled,
  onSave,
}: {
  name: string;
  value: string;
  disabled: boolean;
  onSave: (text: string) => void;
}) {
  const [text, setText] = useState(value);
  const changed = text.trim() !== value && text.trim().length > 0;
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[13px] text-ink-2">{name}</span>
      <Textarea
        value={text}
        rows={name === "Headline" ? 2 : 1}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
        className="min-h-0 resize-none bg-paper"
      />
      {changed && (
        <Button size="sm" className="self-start" disabled={disabled} onClick={() => onSave(text.trim())}>
          Save and check
        </Button>
      )}
    </label>
  );
}

function AskBox({ disabled, onAsk }: { disabled: boolean; onAsk: (text: string) => void }) {
  const [text, setText] = useState("");
  return (
    <form
      className="flex flex-col gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (text.trim().length >= 3) onAsk(text.trim());
      }}
    >
      <label htmlFor="ask" className="placard">
        Ask this slide for a change
      </label>
      <Textarea
        id="ask"
        rows={3}
        maxLength={300}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Make the number the hero; put the points in one column"
        disabled={disabled}
        className="resize-none bg-paper"
      />
      <div className="flex items-center justify-between gap-3">
        <span className="text-[13px] text-ink-2">Layout and emphasis. Colour comes from the look.</span>
        <Button type="submit" size="sm" variant="outline" disabled={disabled || text.trim().length < 3}>
          Ask
        </Button>
      </div>
    </form>
  );
}
