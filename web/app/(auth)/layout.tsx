import Link from "next/link";

import { LanguageReel } from "@/components/language-reel";

// Sign in and sign up: a typographic stage on ink beside a quiet form. No
// screenshots: the stage says what the product does in its own type.
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="grid min-h-dvh lg:grid-cols-[minmax(0,6fr)_minmax(0,5fr)]">
      <section className="flex flex-col justify-between gap-10 bg-ink px-5 py-7 text-paper sm:px-10 lg:min-h-dvh lg:px-14 lg:py-12">
        <Link href="/" className="font-display text-[24px] leading-none tracking-[-0.015em]">
          d-design
        </Link>
        <div className="flex flex-col gap-6">
          <p className="font-display text-[44px] leading-[1.02] tracking-[-0.025em] text-balance sm:text-[60px] xl:text-[76px]">
            One sentence in.
            <br />
            <em className="text-paper/80">A designed deck out.</em>
          </p>
          <p className="max-w-md text-[15px] leading-relaxed text-paper/65">
            Each deck is drawn in its own visual language, every slide is checked in a browser before you see it, and
            it leaves as one file that works offline.
          </p>
        </div>
        <div className="hidden flex-col gap-3 border-t border-paper/15 pt-5 lg:flex">
          <p className="text-[11px] tracking-[0.08em] text-paper/50 uppercase">Eight visual languages · one for each deck</p>
          <LanguageReel className="text-[22px] leading-snug xl:text-[26px]" />
        </div>
      </section>
      <div className="flex items-start justify-center px-5 py-12 sm:px-10 lg:items-center lg:py-0">
        <div className="w-full max-w-sm">{children}</div>
      </div>
    </main>
  );
}
