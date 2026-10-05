"use client";

// The editor (docs/design/app.md § 5): quiet chrome around the slide. Every AI
// change is a proposal shown before/after; every accepted change is a labelled
// version with visible undo (docs/v4/plan/33-trust-control.md). The missing
// colour picker is answered where the user reaches for it (app.md -> "The
// colour picker that does not exist").
import Link from "next/link";
import { useMemo, useState } from "react";

import { SlideThumb } from "@/components/slide-thumb";
import type { Recording } from "@/lib/fixtures";

type Tab = "slide" | "notes" | "design";
interface Version {
  label: string;
  thumbs: Record<string, string>;
}

const STYLE_REACH = /\b(red|blue|green|yellow|orange|purple|pink|black|white|colou?r|font|typeface|bold|italic|bigger|smaller|size)\b/i;
const QUICK = ["Regenerate", "Different layout", "Shorter", "Turn into chart", "Split"] as const;

export function Editor({ deck }: { deck: Recording }) {
  const base = useMemo(() => Object.fromEntries(deck.slides.map((s) => [s.id, s.thumb])), [deck.slides]);
  const [history, setHistory] = useState<Version[]>([{ label: "Generated", thumbs: base }]);
  const [at, setAt] = useState(0);
  const [selected, setSelected] = useState(deck.slides[0]?.id ?? "");
  const [tab, setTab] = useState<Tab>("slide");
  const [proposal, setProposal] = useState<string | null>(null);
  const [reply, setReply] = useState<string | null>(null);
  const [instruction, setInstruction] = useState("");

  const current = history[at] ?? history[0];
  const thumbs = current?.thumbs ?? base;
  const index = deck.slides.findIndex((s) => s.id === selected);
  const plan = deck.outline.find((p) => p.id === selected);
  const look = deck.looks.find((l) => l.id === deck.chosen);
  const canPropose = deck.proposal?.slideId === selected;

  const commit = (label: string, next: Record<string, string>) => {
    setHistory((h) => [...h.slice(0, at + 1), { label, thumbs: next }]);
    setAt((n) => n + 1);
  };

  const ask = (text: string) => {
    setProposal(null);
    if (STYLE_REACH.test(text)) {
      setReply(
        "Colour and type come from the look, so every slide stays one deck. To change them, open Design and pick another palette or pairing — or ask this slide for more emphasis on what matters.",
      );
    } else if (canPropose && /layout/i.test(text) && deck.proposal) {
      setReply(null);
      setProposal(deck.proposal.after);
    } else {
      setReply("Not in this prototype. In the app, this proposes a new version of the slide for you to accept or discard.");
    }
  };

  return (
    <main className="grid h-[calc(100dvh-57px)] grid-cols-[12rem_1fr_22rem] grid-rows-[1fr_auto]">
      <nav aria-label="Slides" className="row-span-2 overflow-y-auto border-r border-rule p-3">
        <ol className="grid gap-3">
          {deck.slides.map((s, i) => (
            <li key={s.id}>
              <button
                type="button"
                aria-current={s.id === selected ? "true" : undefined}
                onClick={() => {
                  setSelected(s.id);
                  setProposal(null);
                  setReply(null);
                }}
                className="grid w-full grid-cols-[1.25rem_1fr] gap-2 text-left text-xs text-ink-2 aria-[current=true]:text-ink"
              >
                <span>{i + 1}</span>
                <span className={s.id === selected ? "outline outline-2 outline-offset-2 outline-ink" : ""}>
                  <SlideThumb src={`/fixtures/${deck.id}/${thumbs[s.id] ?? s.thumb}`} alt={`Slide ${i + 1}`} />
                </span>
              </button>
            </li>
          ))}
        </ol>
      </nav>

      <section aria-label="Canvas" className="grid place-items-center overflow-auto bg-paper-2 p-8">
        {proposal ? (
          <div className="grid w-full max-w-5xl gap-4 md:grid-cols-2">
            <figure>
              <figcaption className="mb-2 text-sm text-ink-2">Now</figcaption>
              <SlideThumb src={`/fixtures/${deck.id}/${thumbs[selected] ?? ""}`} alt="The slide now" />
            </figure>
            <figure>
              <figcaption className="mb-2 text-sm text-ink-2">Proposed — a different layout, same words</figcaption>
              <SlideThumb src={`/fixtures/${deck.id}/${proposal}`} alt="The proposed slide" />
            </figure>
          </div>
        ) : (
          <div className="w-full max-w-5xl">
            <SlideThumb src={`/fixtures/${deck.id}/${thumbs[selected] ?? ""}`} alt={`Slide ${index + 1}`} />
          </div>
        )}
      </section>

      <aside aria-label="Slide panel" className="row-span-2 grid grid-rows-[auto_1fr] border-l border-rule">
        <div role="tablist" className="flex border-b border-rule text-sm">
          {(["slide", "notes", "design"] as const).map((t) => (
            <button
              key={t}
              role="tab"
              type="button"
              aria-selected={tab === t}
              onClick={() => setTab(t)}
              className="flex-1 py-3 capitalize text-ink-2 aria-selected:border-b-2 aria-selected:border-ink aria-selected:text-ink"
            >
              {t}
            </button>
          ))}
        </div>
        <div role="tabpanel" className="overflow-y-auto p-5 text-sm">
          {tab === "slide" && (
            <div className="grid gap-4">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  if (instruction.trim()) ask(instruction);
                }}
                className="grid gap-2"
              >
                <label htmlFor="ask" className="text-ink-2">
                  Ask this slide for a change
                </label>
                <textarea
                  id="ask"
                  rows={3}
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                  placeholder="Lead with the number. Make it more visual."
                  className="border border-rule bg-paper p-2 outline-none focus:border-ink"
                />
                <button type="submit" className="justify-self-start underline">
                  Ask
                </button>
              </form>
              <ul className="flex flex-wrap gap-2">
                {QUICK.map((q) => (
                  <li key={q}>
                    <button type="button" onClick={() => ask(q)} className="rounded-[var(--radius-chrome)] border border-rule px-2 py-1 hover:border-ink">
                      {q}
                    </button>
                  </li>
                ))}
              </ul>
              {canPropose && !proposal && <p className="text-ink-2">Try “Different layout” on this slide.</p>}
              {proposal && (
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      commit(`Different layout on slide ${index + 1}`, { ...thumbs, [selected]: proposal });
                      setProposal(null);
                    }}
                    className="rounded-[var(--radius-chrome)] bg-accent px-4 py-2 font-medium text-accent-ink"
                  >
                    Use it
                  </button>
                  <button type="button" onClick={() => setProposal(null)} className="underline">
                    Keep mine
                  </button>
                </div>
              )}
              {reply && (
                <p role="status" className="border-l-2 border-ink pl-3">
                  {reply}
                </p>
              )}
            </div>
          )}
          {tab === "notes" && (
            <div className="grid gap-2">
              <p className="text-ink-2">What you say on this slide — only you see these.</p>
              <p className="leading-relaxed">{plan?.notes || "No notes on this slide."}</p>
            </div>
          )}
          {tab === "design" && look && (
            <dl className="grid gap-3">
              <div>
                <dt className="text-ink-2">Type</dt>
                <dd>{look.fonts.slice(0, 2).join(" with ")}</dd>
              </div>
              <div>
                <dt className="text-ink-2">Palette</dt>
                <dd>{look.palette}</dd>
              </div>
              <div>
                <dt className="text-ink-2">Grid and texture</dt>
                <dd>
                  {look.grid} · {look.motif}
                </dd>
              </div>
              <p className="mt-2 text-ink-2">
                Colour and type belong to the look, so the deck stays one deck. Change the whole look, a palette variant or the pairing — never one slide by hand. (Not wired in this prototype.)
              </p>
            </dl>
          )}
        </div>
      </aside>

      <footer className="flex items-center justify-between border-t border-rule px-6 py-3 text-sm">
        <div className="flex items-center gap-3">
          <button type="button" disabled={at === 0} onClick={() => setAt((n) => n - 1)} className="underline disabled:no-underline disabled:opacity-40">
            Undo{at > 0 ? `: ${history[at]?.label}` : ""}
          </button>
          <button
            type="button"
            disabled={at >= history.length - 1}
            onClick={() => setAt((n) => n + 1)}
            className="underline disabled:no-underline disabled:opacity-40"
          >
            Redo{at < history.length - 1 ? `: ${history[at + 1]?.label}` : ""}
          </button>
          <span className="text-ink-2">· version {at + 1}</span>
        </div>
        <div className="flex items-center gap-3">
          <a href={`/fixtures/${deck.id}/${deck.exports.present}`} target="_blank" rel="noopener" className="rounded-[var(--radius-chrome)] border border-ink px-4 py-2">
            Present
          </a>
          <Link href={`/deck/${deck.id}/done`} className="rounded-[var(--radius-chrome)] bg-accent px-4 py-2 font-medium text-accent-ink">
            Export
          </Link>
        </div>
      </footer>
    </main>
  );
}
