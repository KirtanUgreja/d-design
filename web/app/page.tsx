import Link from "next/link";

import { Composer } from "@/components/composer";
import { LanguageReel } from "@/components/language-reel";
import { Placard } from "@/components/placard";
import { SlideThumb } from "@/components/slide-thumb";
import { YourDecks } from "@/components/your-decks";
import { asset, loadRecording, recordingIds } from "@/lib/fixtures";

const TYPE: Record<string, string> = {
  pitch: "Pitch",
  sales: "Sales",
  launch: "Launch",
  investor_update: "Investor update",
  partnership: "Partnership",
};

// The real path a deck takes, in order: numbered because order is the point.
const STEPS = [
  { title: "One sentence", body: "Who it is for and what you want from them. Paste notes or numbers too." },
  { title: "A few questions", body: "Answers to pick from, and every one of them skippable." },
  { title: "An outline you approve", body: "Every number traced to you or a cited source. Nothing is built until you say so." },
  { title: "Your deck, checked", body: "Composed slide by slide in its own look, measured in a browser, sent as one offline file." },
];

export default async function Home() {
  const recordings = [];
  for (const id of await recordingIds()) {
    const r = await loadRecording(id);
    if (r.ok) recordings.push(r.value);
  }
  const examples = recordings.map((r) => ({ id: r.id, prompt: r.prompt, type: r.deckType }));
  return (
    <main>
      <section className="mx-auto grid max-w-[1440px] gap-14 px-4 pt-10 pb-16 sm:px-8 sm:pt-16 lg:grid-cols-[minmax(0,8fr)_minmax(0,4fr)] lg:gap-16 lg:pt-20 lg:pb-24">
        <Composer examples={examples} />
        <aside aria-labelledby="how" className="lg:pt-[118px] xl:pt-[150px]">
          <h2 id="how" className="placard">
            How a deck gets made
          </h2>
          <ol className="mt-3 border-t border-rule">
            {STEPS.map((s, i) => (
              <li key={s.title} className="grid grid-cols-[2rem_minmax(0,1fr)] gap-x-3 border-b border-rule py-4">
                <span className="font-display text-[24px] leading-none text-ink-2 tabular-nums">{i + 1}</span>
                <div>
                  <p className="text-[15px] font-medium">{s.title}</p>
                  <p className="mt-0.5 text-sm leading-snug text-ink-2">{s.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </aside>
      </section>

      <div className="mx-auto max-w-[1440px] px-4 sm:px-8">
        <YourDecks />
      </div>

      <section aria-labelledby="languages" className="bg-ink text-paper">
        <div className="mx-auto grid max-w-[1440px] gap-10 px-4 py-16 sm:px-8 sm:py-24 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-16">
          <div>
            <p className="text-[11px] tracking-[0.08em] text-paper/50 uppercase">What makes it yours</p>
            <h2 id="languages" className="mt-3 font-display text-[34px] leading-[1.05] tracking-[-0.02em] sm:text-[44px]">
              Every deck gets its own <em>visual language</em>.
            </h2>
            <p className="mt-5 max-w-md text-[15px] leading-relaxed text-paper/65">
              One of eight is drawn for your words. Every slide is adapted from a reference in it, then checked in a
              browser: nothing overflows, nothing is too small to read, and every number keeps its source.
            </p>
          </div>
          <LanguageReel className="self-center text-[34px] leading-[1.15] tracking-[-0.015em] sm:text-[48px] lg:text-[56px]" />
        </div>
      </section>

      {recordings.length > 0 && (
        <section aria-labelledby="examples" className="mx-auto max-w-[1440px] px-4 py-14 sm:px-8 sm:py-20">
          <div className="mb-6 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
            <h2 id="examples" className="font-display text-[28px] tracking-[-0.015em]">
              Example decks
            </h2>
            <p className="text-sm text-ink-2">Recorded runs, start to finish. Opening one spends nothing.</p>
          </div>
          <ul className="grid gap-x-6 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
            {recordings.map((r) => (
              <li key={r.id}>
                <Link href={`/deck/${r.id}/edit`} className="group block">
                  <SlideThumb src={asset(r.id, r.slides[0]?.thumb ?? "")} alt="" />
                  <Placard label={TYPE[r.deckType] ?? "Deck"} aside={`${r.slides.length} slides`} />
                  <p className="mt-1 line-clamp-2 text-sm leading-snug underline-offset-4 group-hover:underline">
                    {r.thesis}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
