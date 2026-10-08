import Link from "next/link";

import { LanguageReel } from "@/components/language-reel";
import { Logo } from "@/components/logo";

// Sign in and sign up: a quiet type stage on ink beside the form. The logo,
// one line, and the eight visual languages lighting one at a time.
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <section className="flex flex-col justify-between gap-12 bg-ink px-5 py-7 text-paper sm:px-10 lg:min-h-dvh lg:px-14 lg:py-12">
        <Link href="/" aria-label="d-design, home" className="self-start text-[26px]">
          <Logo bar="#b9c98f" />
        </Link>
        <p className="font-display text-[clamp(2.5rem,4.4vw,4.25rem)] leading-[1.04] tracking-[-0.025em]">
          One sentence in.
          <br />
          <em className="text-paper/75">A designed deck out.</em>
        </p>
        <LanguageReel className="hidden max-w-xl text-[20px] leading-snug lg:flex" />
      </section>
      <div className="flex items-start justify-center px-5 py-12 sm:px-10 lg:items-center lg:py-0">
        <div className="w-full max-w-sm">{children}</div>
      </div>
    </main>
  );
}
