"use client";

// The editor for a live deck (docs/v4/plan/28-editor.md): change words, move
// or delete slides, fit a slide its new words broke, try new colours — each a
// job the worker checks in a browser before it is saved, each a labelled
// version undo returns to. No HTML, no free colour picker: the look is the unit
// of style (docs/design/app.md -> "The colour picker that does not exist").
import { useEffect, useState } from "react";

import { SlideThumb } from "@/components/slide-thumb";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { api, type History, type LiveDeck, type Notice } from "@/lib/api/client";

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
}: {
  deck: LiveDeck;
  notice: Notice | null;
  onChange: () => void;
}) {
  const [selected, setSelected] = useState(deck.outline[0]?.id ?? "");
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
  return (
    <div className="grid gap-6 md:grid-cols-[180px_1fr_340px]">
      <ol className="flex flex-col gap-3" aria-label="Slides">
        {deck.outline.map((p, i) => (
          <li key={p.id}>
            <button
              type="button"
              onClick={() => setSelected(p.id)}
              aria-current={p.id === plan.id}
              className={`block w-full text-left ${p.id === plan.id ? "outline-2 outline-offset-2 outline-ink" : ""}`}
            >
              <SlideThumb src={api.thumb(deck.id, p.id, deck.version)} alt={`Slide ${i + 1}`} />
            </button>
          </li>
        ))}
      </ol>

      <div className="grid content-start gap-3">
        <SlideThumb src={api.thumb(deck.id, plan.id, deck.version)} alt={`Slide ${index + 1}, as checked`} />
        <p className="text-sm text-ink-2" aria-live="polite">
          {busy ? `${busy}… checking it in a browser.` : status === "passed" ? "Checked." : status ? "Needs attention: its words no longer fit." : ""}
        </p>
        {status && status !== "passed" && !busy && (
          <Button variant="outline" className="justify-self-start" onClick={() => void run("Fitting the slide", () => api.fit(deck.id, plan.id))}>
            Fit to slide
          </Button>
        )}
        <AskBox
          key={plan.id}
          disabled={!!busy}
          onAsk={(text) => void run("Asking for a change", () => api.ask(deck.id, plan.id, text))}
        />
        {notice?.proposal === plan.id && dismissed !== notice.seq && !busy && (
          <figure className="grid gap-2">
            <figcaption className="text-sm text-ink-2">The change you asked for, checked in a browser:</figcaption>
            <SlideThumb src={api.proposalThumb(deck.id, plan.id, notice.seq)} alt={`Slide ${index + 1}, with your change`} />
            <div className="flex gap-2">
              <Button onClick={() => void run("Applying your change", () => api.accept(deck.id, plan.id))}>Keep this</Button>
              <Button variant="ghost" onClick={() => setDismissed(notice.seq)}>
                Discard
              </Button>
            </div>
          </figure>
        )}
        {(problem || (notice && !busy)) && (
          <Alert variant={problem ? "destructive" : "default"}>
            <AlertDescription>{problem ?? notice?.text}</AlertDescription>
          </Alert>
        )}
      </div>

      <aside className="grid content-start gap-5">
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" disabled={history.at <= 0 || !!busy} onClick={() => void step("undo")}>
            Undo {history.at > 0 ? history.labels[history.at] : ""}
          </Button>
          <Button variant="ghost" size="sm" disabled={history.at >= history.labels.length - 1 || !!busy} onClick={() => void step("redo")}>
            Redo
          </Button>
        </div>
        <Separator />
        <h2 className="font-display text-xl">Slide {index + 1}</h2>
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
            disabled={!!busy || ends.has(plan.id) || deck.outline.length <= 3}
            onClick={() => void run("Deleting the slide", () => api.remove(deck.id, plan.id))}
          >
            Delete slide
          </Button>
        </div>
        <Separator />
        <div className="grid gap-2">
          <h2 className="font-display text-xl">Colours</h2>
          <p className="text-sm text-ink-2">
            Colour and type come from the deck&apos;s look, so every slide stays one deck. Try another palette; the layouts stay.
          </p>
          <Button variant="outline" className="justify-self-start" disabled={!!busy} onClick={() => void run("Trying new colours", () => api.recolour(deck.id))}>
            New colours
          </Button>
        </div>
      </aside>
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
    <label className="grid gap-1.5">
      <span className="text-xs uppercase tracking-wider text-ink-2">{name}</span>
      <Textarea value={text} rows={name === "Headline" ? 2 : 1} onChange={(e) => setText(e.target.value)} disabled={disabled} />
      {changed && (
        <Button size="sm" className="justify-self-start" disabled={disabled} onClick={() => onSave(text.trim())}>
          Save
        </Button>
      )}
    </label>
  );
}

function AskBox({ disabled, onAsk }: { disabled: boolean; onAsk: (text: string) => void }) {
  const [text, setText] = useState("");
  return (
    <form
      className="grid gap-2"
      onSubmit={(e) => {
        e.preventDefault();
        if (text.trim().length >= 3) onAsk(text.trim());
      }}
    >
      <label htmlFor="ask" className="text-sm">
        Ask this slide for a change
      </label>
      <Textarea
        id="ask"
        rows={2}
        maxLength={300}
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Make the number the hero; put the points in one column"
        disabled={disabled}
      />
      <Button type="submit" size="sm" variant="outline" className="justify-self-start" disabled={disabled || text.trim().length < 3}>
        Ask
      </Button>
    </form>
  );
}
