import Link from "next/link";

import { Composer } from "@/components/composer";
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

export default async function Home() {
  const recordings = [];
  for (const id of await recordingIds()) {
    const r = await loadRecording(id);
    if (r.ok) recordings.push(r.value);
  }
  const examples = recordings.map((r) => ({ id: r.id, prompt: r.prompt, type: r.deckType }));
  const featured = recordings[0];
  return (
    <main className="mx-auto max-w-[1440px] px-4 sm:px-8">
      <section className="grid gap-12 py-10 sm:py-16 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-16 lg:py-20">
        <Composer examples={examples} />
        {featured && (
          <figure className="hidden min-w-0 self-start lg:mt-[104px] lg:block">
            <Link href={`/deck/${featured.id}/edit`} className="group block">
              <SlideThumb src={asset(featured.id, featured.slides[0]?.thumb ?? "")} alt="The cover of an example deck" />
              <Placard lead="Example" label={TYPE[featured.deckType] ?? "Deck"} aside="Open it →" />
            </Link>
            <figcaption className="mt-2 text-sm leading-snug text-ink-2">
              Made from one line: <span className="text-ink">“{featured.prompt}”</span>
            </figcaption>
          </figure>
        )}
      </section>
      <YourDecks />
      {recordings.length > 0 && (
        <section aria-labelledby="examples" className="border-t border-rule py-10">
          <div className="mb-6 flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1">
            <h2 id="examples" className="font-display text-2xl tracking-[-0.01em]">
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
