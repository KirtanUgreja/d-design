// What makes a deck from here different, each shown as the piece of the
// product that does it rather than an icon: the questions, the source marks,
// the measurement (docs/v4/spec.md: designed, says something, every number
// traced).
export function Proofs() {
  return (
    <section aria-labelledby="how" className="border-t border-rule">
      <div className="mx-auto max-w-[1440px] px-4 py-14 sm:px-8 sm:py-20">
        <h2 id="how" className="sr-only">
          How a deck is made
        </h2>
        <ol className="grid gap-10 md:grid-cols-3 md:gap-8">
          <Proof step="It asks first" body="A few questions about your audience, your proof and your ask, so the deck argues your point instead of a generic one.">
            <div className="flex flex-col gap-2">
              <p className="text-[13px] text-ink-2">Who is in the room?</p>
              <p className="border-b border-ink pb-1 text-[14px]">Seed investors, ten minutes, live</p>
              <p className="pt-2 text-[13px] text-ink-2">What proof do you have?</p>
              <p className="border-b border-rule pb-1 text-[14px] text-ink-2">
                400 sign-ups in six weeks<span className="ml-0.5 inline-block h-[1.05em] w-px translate-y-[2px] animate-pulse bg-ink" />
              </p>
            </div>
          </Proof>
          <Proof step="Every number has a source" body="Each figure traces to you or to a page it read. You approve them before a single slide is drawn.">
            <ul className="flex flex-col gap-2.5 text-[14px]">
              <Line value="400+" label="sign-ups" mark="YOU" />
              <Line value="47%" label="of projects miss their goals" mark="WEB" />
              <Line value="$225B" label="low-code spend by 2029" mark="WEB" />
            </ul>
          </Proof>
          <Proof step="Every slide is measured" body="Each slide is rendered in a real browser and checked for overflow, contrast and crowding before you see it.">
            <div className="relative aspect-video border border-rule bg-ink">
              <span className="absolute top-[18%] left-[8%] h-[16%] w-[52%] outline outline-1 outline-dashed outline-paper/60" />
              <span className="absolute top-[44%] left-[8%] h-[30%] w-[30%] outline outline-1 outline-dashed outline-paper/60" />
              <span className="absolute top-[18%] right-[8%] h-[56%] w-[26%] outline outline-1 outline-dashed outline-paper/60" />
              <span className="absolute right-2 bottom-2 bg-paper px-1.5 py-0.5 font-mono text-[10px] tracking-wide text-ink uppercase">
                Passed · 0 defects
              </span>
            </div>
          </Proof>
        </ol>
      </div>
    </section>
  );
}

function Proof({ step, body, children }: { step: string; body: string; children: React.ReactNode }) {
  return (
    <li className="flex flex-col gap-5">
      <div className="min-h-[9.5rem] border border-rule bg-paper-2/50 p-5">{children}</div>
      <div>
        <h3 className="font-display text-[20px] leading-snug">{step}</h3>
        <p className="mt-1.5 max-w-[42ch] text-sm text-ink-2">{body}</p>
      </div>
    </li>
  );
}

function Line({ value, label, mark }: { value: string; label: string; mark: "YOU" | "WEB" }) {
  return (
    <li className="flex items-baseline gap-2 border-b border-rule pb-1.5">
      <span className="font-medium tabular-nums">{value}</span>
      <span className="truncate text-ink-2">{label}</span>
      <span className="ml-auto border border-ink px-1 font-mono text-[10px] leading-4">{mark}</span>
    </li>
  );
}
