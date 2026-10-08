"use client";
// The eight visual languages, one lit at a time: every deck is drawn in one of
// them, chosen for its words (docs/v4/plan/39-design-reset.md). It holds still
// under reduced motion.
import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

export const LANGUAGES = [
  "Swiss grid",
  "Magazine editorial",
  "Type poster",
  "Cinematic",
  "Data journal",
  "Quiet minimal",
  "Geometric modern",
  "Warm humanist",
] as const;

export function LanguageReel({ className, every = 1700 }: { className?: string; every?: number }) {
  const [at, setAt] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timer = window.setInterval(() => setAt((a) => (a + 1) % LANGUAGES.length), every);
    return () => window.clearInterval(timer);
  }, [every]);
  return (
    <ul aria-label="The eight visual languages" className={cn("flex flex-wrap gap-x-[0.6em] gap-y-1 font-display", className)}>
      {LANGUAGES.map((name, i) => (
        <li key={name} className={cn("transition-colors duration-700", i === at ? "text-paper" : "text-paper/25")}>
          {name}
          {i < LANGUAGES.length - 1 && (
            <span aria-hidden="true" className="text-paper/25">
              ,
            </span>
          )}
        </li>
      ))}
    </ul>
  );
}
