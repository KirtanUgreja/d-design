// The reveal (docs/design/app.md § 6; docs/v4/plan/32-watch-reveal.md): the
// end of the experience. The deck itself, large; three exports in human words;
// flagged slides named before anything is downloaded.
import Link from "next/link";

import { SlideThumb } from "@/components/slide-thumb";
import { StepBar } from "@/components/step-bar";
import { getDeck, type DeckParams } from "@/lib/deck";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default async function DonePage(props: DeckParams) {
  const deck = await getDeck(props);
  const file = (f: string) => `/fixtures/${deck.id}/${f}`;
  const flagged = deck.slides.filter((s) => s.status !== "passed");
  const [cover, ...rest] = deck.slides;
  return (
    <>
      <StepBar deckId={deck.id} current="deck" />
      <main className="grid gap-10 px-8 py-10 md:grid-cols-[7fr_5fr]">
        <section aria-label="Your deck" className="grid content-start gap-4">
          {cover && <SlideThumb src={file(cover.thumb)} alt="The cover" />}
          <ul className="grid grid-cols-4 gap-3">
            {rest.map((s, i) => (
              <li key={s.id}>
                <SlideThumb src={file(s.thumb)} alt={`Slide ${i + 2}`} />
              </li>
            ))}
          </ul>
        </section>
        <section aria-labelledby="ready" className="grid content-start gap-6">
          <div>
            <h1 id="ready" className="font-display text-4xl leading-tight">
              {deck.thesis}
            </h1>
            <p className="mt-2 text-ink-2">{deck.slides.length} slides · one file · works offline, anywhere</p>
          </div>
          {flagged.length > 0 && (
            <Alert variant="destructive">
              <AlertTitle>
                {flagged.length} slide{flagged.length > 1 ? "s need" : " needs"} attention before you send it
              </AlertTitle>
              <AlertDescription>
                {flagged.map((s) => s.id).join(", ")} ·{" "}
                <Link href={`/deck/${deck.id}/edit`} className="underline">
                  Open in the editor
                </Link>
              </AlertDescription>
            </Alert>
          )}
          <ul className="grid gap-3">
            <li>
              <a href={file(deck.exports.present)} target="_blank" rel="noopener" className="block border border-ink px-5 py-4 hover:bg-paper-2">
                <span className="block font-medium">Present</span>
                <span className="text-sm text-ink-2">For you: your speaker notes are inside. Press P for the presenter view.</span>
              </a>
            </li>
            <li>
              <a href={file(deck.exports.send)} download={`${deck.id}.html`} className="block bg-accent px-5 py-4 text-accent-ink">
                <span className="block font-medium">Download to send</span>
                <span className="text-sm opacity-90">For them: the slides only, as one file that opens in any browser.</span>
              </a>
            </li>
            <li>
              <a href={file(deck.exports.pdf)} download={`${deck.id}.pdf`} className="block px-5 py-3 text-sm underline">
                PDF, one slide per page
              </a>
            </li>
          </ul>
          <p className="text-xs text-ink-2">Arrow keys move, F is fullscreen, O shows every slide. The file says it was made with AI.</p>
        </section>
      </main>
    </>
  );
}
