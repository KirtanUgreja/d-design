import Link from "next/link";

import { Composer } from "@/components/composer";
import { SlideThumb } from "@/components/slide-thumb";
import { PrototypeNote } from "@/components/step-bar";
import { asset, loadRecording, recordingIds } from "@/lib/fixtures";

export default async function Home() {
  const recordings = [];
  for (const id of await recordingIds()) {
    const r = await loadRecording(id);
    if (r.ok) recordings.push(r.value);
  }
  const examples = recordings.map((r) => ({ id: r.id, prompt: r.prompt, type: r.deckType }));
  return (
    <main className="mx-auto grid min-h-dvh max-w-6xl grid-rows-[auto_1fr_auto] px-8">
      <header className="flex items-center gap-6 py-6">
        <span className="font-display text-xl tracking-tight">d-design</span>
        <PrototypeNote />
      </header>
      <section className="grid content-center gap-10 pb-16 md:grid-cols-[7fr_5fr] md:gap-16">
        <Composer examples={examples} />
        {recordings[0] && (
          <figure className="hidden self-center md:block">
            <SlideThumb src={asset(recordings[0].id, recordings[0].slides[0]?.thumb ?? "")} alt="" />
            <figcaption className="mt-3 text-sm text-ink-2">
              A real deck from a one-line brief: composed, measured and cited.
            </figcaption>
          </figure>
        )}
      </section>
      {recordings.length > 0 && (
        <section aria-labelledby="recent" className="border-t border-rule py-8">
          <h2 id="recent" className="mb-4 text-sm font-medium text-ink-2">
            Recent
          </h2>
          <ul className="grid grid-cols-2 gap-6 md:grid-cols-4">
            {recordings.map((r) => (
              <li key={r.id}>
                <Link href={`/deck/${r.id}/edit`} className="group block">
                  <SlideThumb src={asset(r.id, r.slides[0]?.thumb ?? "")} alt="" />
                  <span className="mt-2 block text-sm group-hover:underline">{r.thesis}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
