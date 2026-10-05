"use client";

// The first screen is the proof (docs/v4/ui-research.md, rule 1): one prompt
// box, a real brief as the placeholder, real example briefs as chips. No
// templates, no tour, no form above the prompt (docs/design/app.md § 1).
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

interface Example {
  id: string;
  prompt: string;
  type: string;
}

const TYPE_LABEL: Record<string, string> = {
  pitch: "Pitch",
  sales: "Sales",
  launch: "Launch",
  investor_update: "Investor update",
  partnership: "Partnership",
};

export function Composer({ examples }: { examples: Example[] }) {
  const router = useRouter();
  const [text, setText] = useState("");
  const [picked, setPicked] = useState<string | null>(null);
  const label = useId();
  const first = examples[0];

  const start = () => {
    // ponytail: the prototype has two recorded runs; a typed brief replays the
    // closest one. Phase 27 starts a real generation here.
    const target = picked ?? first?.id;
    if (target) router.push(`/deck/${target}/outline`);
  };

  return (
    <form
      className="grid gap-5"
      onSubmit={(e) => {
        e.preventDefault();
        start();
      }}
    >
      <label htmlFor={label} className="font-display text-4xl leading-tight tracking-tight md:text-5xl">
        What are you presenting?
      </label>
      <div className="border border-ink bg-paper focus-within:outline-2 focus-within:outline-accent">
        <textarea
          id={label}
          autoFocus
          rows={4}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setPicked(null);
          }}
          placeholder={first?.prompt ?? "Series A pitch for our CI tool, to seed-stage investors"}
          className="block w-full resize-none bg-transparent p-4 text-lg outline-none placeholder:text-ink-2"
        />
        <div className="flex items-center justify-between border-t border-rule px-4 py-3">
          <span className="text-sm text-ink-2">Paste notes or numbers into the box — they become your facts.</span>
          <Button type="submit" size="lg">
            Start
          </Button>
        </div>
      </div>
      {examples.length > 0 && (
        <div className="grid gap-2">
          <p className="text-sm text-ink-2">Or start from a real brief:</p>
          <ToggleGroup
            type="single"
            variant="outline"
            spacing={2}
            value={picked ?? ""}
            onValueChange={(id) => {
              const x = examples.find((e) => e.id === id);
              setPicked(x ? x.id : null);
              if (x) setText(x.prompt);
            }}
            className="flex-wrap"
          >
            {examples.map((x) => (
              <ToggleGroupItem key={x.id} value={x.id} className="h-auto py-1.5 text-left">
                <span className="text-muted-foreground">{TYPE_LABEL[x.type] ?? x.type} ·</span>
                {x.prompt.length > 70 ? `${x.prompt.slice(0, 70)}…` : x.prompt}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>
      )}
    </form>
  );
}
