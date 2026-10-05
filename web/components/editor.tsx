"use client";

// The editor (docs/design/app.md § 5): quiet chrome around the slide. Every AI
// change is a proposal shown before/after; every accepted change is a labelled
// version with visible undo (docs/v4/plan/33-trust-control.md). The missing
// colour picker is answered where the user reaches for it (app.md -> "The
// colour picker that does not exist").
import Link from "next/link";
import { useMemo, useState } from "react";

import { SlideThumb } from "@/components/slide-thumb";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import type { Recording } from "@/lib/fixtures";

interface Version {
  label: string;
  thumbs: Record<string, string>;
}

const STYLE_REACH =
  /\b(red|blue|green|yellow|orange|purple|pink|black|white|colou?r|font|typeface|bold|italic|bigger|smaller|size)\b/i;
const QUICK = ["Regenerate", "Different layout", "Shorter", "Turn into chart", "Split"] as const;

export function Editor({ deck }: { deck: Recording }) {
  const base = useMemo(() => Object.fromEntries(deck.slides.map((s) => [s.id, s.thumb])), [deck.slides]);
  const [history, setHistory] = useState<Version[]>([{ label: "Generated", thumbs: base }]);
  const [at, setAt] = useState(0);
  const [selected, setSelected] = useState(deck.slides[0]?.id ?? "");
  const [proposal, setProposal] = useState<string | null>(null);
  const [reply, setReply] = useState<string | null>(null);
  const [instruction, setInstruction] = useState("");

  const thumbs = (history[at] ?? history[0])?.thumbs ?? base;
  const index = deck.slides.findIndex((s) => s.id === selected);
  const plan = deck.outline.find((p) => p.id === selected);
  const look = deck.looks.find((l) => l.id === deck.chosen);
  const canPropose = deck.proposal?.slideId === selected;
  const src = (file: string | undefined) => `/fixtures/${deck.id}/${file ?? ""}`;

  const commit = (label: string, next: Record<string, string>) => {
    setHistory((h) => [...h.slice(0, at + 1), { label, thumbs: next }]);
    setAt((n) => n + 1);
  };

  const ask = (text: string) => {
    setProposal(null);
    if (STYLE_REACH.test(text)) {
      setReply(
        "Colour and type come from the look, so every slide stays one deck. Open Design to pick another palette or pairing — or ask this slide for more emphasis on what matters.",
      );
    } else if (/new look/i.test(text)) {
      setReply("Not in this prototype. In the app, this generates a new look for the whole deck and shows it before/after.");
    } else if (canPropose && /layout/i.test(text) && deck.proposal) {
      setReply(null);
      setProposal(deck.proposal.after);
    } else {
      setReply("Not in this prototype. In the app, this proposes a new version of the slide for you to accept or discard.");
    }
  };

  return (
    <main className="grid min-h-[calc(100dvh-57px)] grid-cols-1 lg:h-[calc(100dvh-57px)] lg:grid-cols-[12rem_1fr_22rem] lg:grid-rows-[1fr_auto]">
      <nav aria-label="Slides" className="overflow-x-auto border-b border-rule p-3 lg:row-span-2 lg:overflow-y-auto lg:border-r lg:border-b-0">
        <ol className="flex gap-3 lg:flex-col">
          {deck.slides.map((s, i) => (
            <li key={s.id} className="w-32 shrink-0 lg:w-auto">
              <button
                type="button"
                aria-current={s.id === selected ? "true" : undefined}
                onClick={() => {
                  setSelected(s.id);
                  setProposal(null);
                  setReply(null);
                }}
                className="grid w-full grid-cols-[1.25rem_1fr] gap-2 text-left text-xs text-muted-foreground aria-[current=true]:text-foreground"
              >
                <span>{i + 1}</span>
                <span className={s.id === selected ? "outline outline-2 outline-offset-2 outline-ink" : ""}>
                  <SlideThumb src={src(thumbs[s.id] ?? s.thumb)} alt={`Slide ${i + 1}`} />
                </span>
              </button>
            </li>
          ))}
        </ol>
      </nav>

      <section aria-label="Canvas" className="grid place-items-center overflow-auto bg-muted p-8">
        {proposal ? (
          <div className="grid w-full max-w-5xl gap-4 md:grid-cols-2">
            <figure className="flex flex-col gap-2">
              <figcaption className="text-sm text-muted-foreground">Now</figcaption>
              <SlideThumb src={src(thumbs[selected])} alt="The slide now" />
            </figure>
            <figure className="flex flex-col gap-2">
              <figcaption className="text-sm text-muted-foreground">Proposed — a different layout, same words</figcaption>
              <SlideThumb src={src(proposal)} alt="The proposed slide" className="outline outline-2 outline-offset-4 outline-accent" />
            </figure>
          </div>
        ) : (
          <div className="w-full max-w-5xl">
            <SlideThumb src={src(thumbs[selected])} alt={`Slide ${index + 1}`} />
          </div>
        )}
      </section>

      <aside aria-label="Slide panel" className="border-t border-rule lg:row-span-2 lg:overflow-y-auto lg:border-t-0 lg:border-l">
        <Tabs defaultValue="slide" className="gap-0">
          <TabsList variant="line" className="w-full border-b border-rule px-2">
            <TabsTrigger value="slide">Slide</TabsTrigger>
            <TabsTrigger value="notes">Notes</TabsTrigger>
            <TabsTrigger value="design">Design</TabsTrigger>
          </TabsList>
          <TabsContent value="slide" className="flex flex-col gap-4 p-5 text-sm">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (instruction.trim()) ask(instruction);
              }}
              className="flex flex-col gap-2"
            >
              <label htmlFor="ask" className="text-muted-foreground">
                Ask this slide for a change
              </label>
              <Textarea
                id="ask"
                rows={3}
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="Lead with the number. Make it more visual."
              />
              <Button type="submit" variant="outline" className="self-start">
                Ask
              </Button>
            </form>
            <ul className="flex flex-wrap gap-2">
              {QUICK.map((q) => (
                <li key={q}>
                  <Button variant="outline" size="sm" onClick={() => ask(q)}>
                    {q}
                  </Button>
                </li>
              ))}
            </ul>
            {canPropose && !proposal && <p className="text-muted-foreground">Try “Different layout” on this slide.</p>}
            {proposal && (
              <div className="flex gap-2">
                <Button
                  onClick={() => {
                    commit(`Different layout on slide ${index + 1}`, { ...thumbs, [selected]: proposal });
                    setProposal(null);
                  }}
                >
                  Use it
                </Button>
                <Button variant="ghost" onClick={() => setProposal(null)}>
                  Keep mine
                </Button>
              </div>
            )}
            {reply && (
              <Alert role="status">
                <AlertDescription>{reply}</AlertDescription>
              </Alert>
            )}
          </TabsContent>
          <TabsContent value="notes" className="flex flex-col gap-2 p-5 text-sm">
            <p className="text-muted-foreground">What you say on this slide — only you see these.</p>
            <p className="leading-relaxed">{plan?.notes || "No notes on this slide."}</p>
          </TabsContent>
          <TabsContent value="design" className="p-5 text-sm">
            {look && (
              <dl className="flex flex-col gap-3">
                <div>
                  <dt className="text-muted-foreground">Type</dt>
                  <dd>{look.fonts.slice(0, 2).join(" with ")}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Palette</dt>
                  <dd>{look.palette}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Grid and texture</dt>
                  <dd>
                    {look.grid} · {look.motif}
                  </dd>
                </div>
                <Separator className="my-1" />
                <p className="text-muted-foreground">
                  This look was generated for this deck — no other deck has it. Colour and type belong to the look, so
                  every slide stays one deck.
                </p>
                <Button variant="outline" className="self-start" onClick={() => ask("new look")}>
                  Try another look
                </Button>
              </dl>
            )}
          </TabsContent>
        </Tabs>
      </aside>

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-rule px-6 py-3 text-sm">
        <div className="flex items-center gap-1">
          <Button variant="ghost" disabled={at === 0} onClick={() => setAt((n) => n - 1)}>
            Undo{at > 0 ? `: ${history[at]?.label}` : ""}
          </Button>
          <Button variant="ghost" disabled={at >= history.length - 1} onClick={() => setAt((n) => n + 1)}>
            Redo{at < history.length - 1 ? `: ${history[at + 1]?.label}` : ""}
          </Button>
          <span className="text-muted-foreground">· version {at + 1}</span>
        </div>
        <div className="flex items-center gap-2">
          <Button asChild variant="outline" size="lg">
            <a href={src(deck.exports.present)} target="_blank" rel="noopener">
              Present
            </a>
          </Button>
          <Button asChild size="lg">
            <Link href={`/deck/${deck.id}/done`}>Export</Link>
          </Button>
        </div>
      </footer>
    </main>
  );
}
