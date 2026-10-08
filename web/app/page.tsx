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

// A word or two per recorded example, for its chip.
const SHORT: Record<string, string> = { "launch-product": "Tessel 2", "pitch-tesla": "Tesla", "update-q3": "Harbor" };

export default async function Home() {
  const recordings = [];
  for (const id of await recordingIds()) {
    const r = await loadRecording(id);
    if (r.ok) recordings.push(r.value);
  }
  const examples = recordings.map((r) => ({
    id: r.id,
    prompt: r.prompt,
    type: r.deckType,
    short: SHORT[r.id] ?? r.prompt.split(" ").slice(0, 3).join(" "),
  }));
  return (
    <main>
      <section className="mx-auto max-w-[920px] px-4 pt-14 pb-20 sm:px-8 sm:pt-24 sm:pb-28">
        <Composer examples={examples} />
      </section>

      <div className="mx-auto max-w-[1440px] px-4 sm:px-8">
        <YourDecks />
      </div>

      <section aria-labelledby="languages" className="bg-ink text-paper">
        <div className="mx-auto grid max-w-[1440px] items-center gap-10 px-4 py-16 sm:px-8 sm:py-24 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)] lg:gap-16">
          <h2 id="languages" className="font-display text-[34px] leading-[1.05] tracking-[-0.02em] sm:text-[44px]">
            Every deck gets its own <em>visual language</em>.
          </h2>
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
