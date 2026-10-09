// The wall: real slides from decks this engine built (2026-10-10, the owner's
// best-rated runs), drifting in two rows like prints passing on a gallery
// wall. What a person gets is the first proof (docs/v4/ui-research.md, rule 1).
// Still under reduced motion; paused while the pointer is on it.
/* eslint-disable @next/next/no-img-element -- our own 768px webp, sized by us */
import { cn } from "@/lib/utils";

interface Print {
  n: string;
  look: string;
  kind: string;
}

const ROWS: Print[][] = [
  [
    { n: "01", look: "Studio", kind: "Pitch" },
    { n: "02", look: "Cinematic", kind: "Launch" },
    { n: "03", look: "Bright", kind: "Sales" },
    { n: "04", look: "Cinematic", kind: "Partnership" },
    { n: "05", look: "Studio", kind: "Pitch" },
    { n: "06", look: "Frame", kind: "Partnership" },
    { n: "07", look: "Soft", kind: "Investor update" },
    { n: "08", look: "Cinematic", kind: "Launch" },
    { n: "09", look: "Bright", kind: "Sales" },
    { n: "10", look: "Studio", kind: "Pitch" },
  ],
  [
    { n: "11", look: "Cinematic", kind: "Partnership" },
    { n: "12", look: "Soft", kind: "Investor update" },
    { n: "13", look: "Frame", kind: "Partnership" },
    { n: "14", look: "Studio", kind: "Pitch" },
    { n: "15", look: "Bright", kind: "Sales" },
    { n: "16", look: "Cinematic", kind: "Launch" },
    { n: "17", look: "Frame", kind: "Partnership" },
    { n: "18", look: "Soft", kind: "Investor update" },
    { n: "19", look: "Cinematic", kind: "Partnership" },
    { n: "20", look: "Bright", kind: "Sales" },
  ],
];

export function Showcase() {
  return (
    <section aria-labelledby="wall" className="overflow-hidden py-14 sm:py-20">
      <div className="mx-auto mb-8 flex max-w-[1440px] flex-wrap items-end justify-between gap-x-8 gap-y-2 px-4 sm:px-8">
        <h2 id="wall" className="font-display text-[26px] leading-tight tracking-[-0.01em] sm:text-[30px]">
          Slides it designed, <em>unedited</em>.
        </h2>
        <p className="max-w-[46ch] text-sm text-ink-2">
          Every deck gets its own visual language, chosen for its words. Nothing here is a template.
        </p>
      </div>
      <div className="group flex flex-col gap-5" aria-hidden="true">
        {ROWS.map((row, r) => (
          <div key={r} className="flex w-max">
            {/* Two copies of the row: the track slides by one copy, then repeats. */}
            <ul
              className={cn(
                "flex w-max gap-5 pr-5 group-hover:[animation-play-state:paused]",
                r === 0 ? "animate-[drift_90s_linear_infinite]" : "animate-[drift_110s_linear_infinite_reverse]",
              )}
            >
              {[...row, ...row].map((p, i) => (
                <li key={`${p.n}-${i}`} className="w-[300px] shrink-0 sm:w-[384px]">
                  <img
                    src={`/showcase/${p.n}.webp`}
                    alt=""
                    width={768}
                    height={432}
                    loading={i < 5 ? "eager" : "lazy"}
                    className="block aspect-video w-full border border-rule bg-paper-2"
                    draggable={false}
                  />
                  <p className="mt-2 flex items-baseline gap-2 placard">
                    <span className="text-ink">{p.look}</span>
                    <span>{p.kind}</span>
                  </p>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </section>
  );
}
