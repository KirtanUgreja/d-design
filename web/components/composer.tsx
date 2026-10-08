"use client";

// The first screen is the proof (docs/v4/ui-research.md, rule 1): one prompt
// box, a real brief as the placeholder, real example briefs as chips. No
// templates, no tour, no form above the prompt (docs/design/app.md § 1).
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { authClient } from "@/lib/auth-client";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";

// A brief typed before signing in survives sign-up (phase 31, A5): kept in
// this tab only, and started the moment the person is signed in.
const PENDING = "dd:pending-brief";

function remember(text: string): void {
  try {
    sessionStorage.setItem(PENDING, text);
  } catch {
    // storage blocked: the person retypes it; nothing breaks
  }
}

function takePending(): string {
  try {
    const text = sessionStorage.getItem(PENDING) ?? "";
    sessionStorage.removeItem(PENDING);
    return text;
  } catch {
    return "";
  }
}

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
  auto: "Pitch",
};

export function Composer({ examples }: { examples: Example[] }) {
  const router = useRouter();
  const [text, setText] = useState("");
  const [picked, setPicked] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const label = useId();
  const first = examples[0];

  const start = async () => {
    // A recorded brief replays its recording; anything else is a real deck,
    // built by the API and the worker (phase 27).
    // Only a picked example (or an empty box) replays a recording: anything
    // typed is a real deck, even if it reads like an example.
    const target = picked ?? (text.trim() ? null : first?.id);
    if (target) {
      router.push(`/deck/${target}/outline`);
      return;
    }
    setNotice(null);
    const session = await authClient.getSession();
    if (!session.data) {
      remember(text.trim());
      router.push(`/sign-up?next=${encodeURIComponent("/")}`);
      return;
    }
    await create(text.trim());
  };

  const create = async (brief: string) => {
    const made = await api.create(brief);
    if (made.ok) {
      router.push(`/d/${made.value.id}`);
      return;
    }
    setNotice(`${made.error} Until it is, pick one of the recorded briefs below.`);
  };

  // Back from sign-up or sign-in with a brief waiting: start it.
  useEffect(() => {
    let live = true;
    const resume = async () => {
      const session = await authClient.getSession();
      if (!live || !session.data) return;
      const brief = takePending();
      if (!brief) return;
      setText(brief);
      await create(brief);
    };
    void resume();
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once, on arrival
  }, []);

  return (
    <form
      className="flex min-w-0 flex-col gap-6"
      onSubmit={(e) => {
        e.preventDefault();
        void start();
      }}
    >
      <label
        htmlFor={label}
        className="font-display text-[40px] leading-[1.04] tracking-[-0.02em] text-balance sm:text-[56px]"
      >
        What are you presenting?
      </label>
      <div className="border border-ink bg-paper transition-colors focus-within:border-accent focus-within:ring-1 focus-within:ring-accent">
        <textarea
          id={label}
          autoFocus
          rows={3}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setPicked(null);
            setNotice(null);
          }}
          placeholder={first?.prompt ?? "Series A pitch for our CI tool, to seed-stage investors"}
          className="block min-h-[9.5rem] w-full resize-none bg-transparent px-5 pt-5 pb-3 font-display text-[22px] leading-[1.35] outline-none placeholder:text-ink-2/70 focus-visible:outline-none sm:min-h-0 sm:px-6 sm:text-[26px]"
        />
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-rule px-5 py-3 sm:px-6">
          <span className="text-[13px] text-ink-2">Paste notes or numbers too: they become your facts.</span>
          <Button type="submit" size="lg" className="ml-auto px-6">
            Start <span aria-hidden="true">→</span>
          </Button>
        </div>
      </div>
      {notice && (
        <p role="status" className="border-l-2 border-flag pl-3 text-sm">
          {notice}
        </p>
      )}
      {examples.length > 0 && (
        <div className="flex flex-col gap-3">
          <p className="placard">Or start from a real brief</p>
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
            className="w-full flex-wrap justify-start"
          >
            {examples.map((x) => (
              <ToggleGroupItem
                key={x.id}
                value={x.id}
                className="h-auto max-w-full min-w-0 justify-start gap-1.5 px-3 py-1.5 text-left text-[13px] data-[state=on]:border-ink"
              >
                <span className="shrink-0 text-ink-2">{TYPE_LABEL[x.type] ?? "Deck"} ·</span>
                <span className="truncate">{x.prompt}</span>
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>
      )}
    </form>
  );
}
