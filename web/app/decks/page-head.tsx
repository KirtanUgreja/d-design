import Link from "next/link";

import { cn } from "@/lib/utils";

// The header the signed-in pages share: the wordmark, a new deck, the two
// account surfaces.
export function PageHead({ current }: { current: "decks" | "account" }) {
  const link = (href: string, label: string, here: boolean) => (
    <Link href={href} aria-current={here ? "page" : undefined} className={cn("underline-offset-4 hover:underline", here && "text-ink")}>
      {label}
    </Link>
  );
  return (
    <header className="flex items-baseline gap-8 border-b border-rule py-6">
      <Link href="/" className="font-display text-xl tracking-tight">
        d-design
      </Link>
      <nav aria-label="Account" className="flex gap-6 text-sm text-ink-2">
        {link("/", "New deck", false)}
        {link("/decks", "Your decks", current === "decks")}
        {link("/account", "Account", current === "account")}
      </nav>
    </header>
  );
}
