// The path is short and named, the current step marked (docs/v4/ui-research.md
// -> goal-gradient). Links back only to steps already passed.
import Link from "next/link";

const STEPS = [
  { key: "brief", label: "Brief", href: () => "/" },
  { key: "outline", label: "Outline", href: (id: string) => `/deck/${id}/outline` },
  { key: "deck", label: "Deck", href: (id: string) => `/deck/${id}/edit` },
] as const;

export type Step = (typeof STEPS)[number]["key"];

export function StepBar({ deckId, current }: { deckId: string; current: Step }) {
  const at = STEPS.findIndex((s) => s.key === current);
  return (
    <nav aria-label="Steps" className="flex items-center gap-6 border-b border-rule px-8 py-4 text-sm">
      <Link href="/" className="font-display text-lg tracking-tight">
        d-design
      </Link>
      <ol className="flex items-center gap-2 text-ink-2">
        {STEPS.map((s, i) => (
          <li key={s.key} className="flex items-center gap-2">
            {i > 0 && <span aria-hidden="true">→</span>}
            {i < at ? (
              <Link href={s.href(deckId)} className="underline-offset-4 hover:underline">
                {s.label}
              </Link>
            ) : (
              <span aria-current={i === at ? "step" : undefined} className={i === at ? "font-medium text-ink" : ""}>
                {s.label}
              </span>
            )}
          </li>
        ))}
      </ol>
      <PrototypeNote />
    </nav>
  );
}

export function PrototypeNote() {
  return (
    <p className="ml-auto text-xs text-ink-2">
      Prototype — replaying a real recorded run. <Link href="/states" className="underline">States</Link>
    </p>
  );
}
