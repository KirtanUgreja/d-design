# Phase 02 comps

Three hand-written scenes, real HTML and CSS, real copy — d-design's own launch copy, since that is the actual product this repo is building. No React, no renderer, no Motion library: phase 04 wires those up against the values extracted here.

## View them

```
cd docs/v1/comps && python3 -m http.server 8000
```

Open `http://localhost:8000/hero.html`. Each page links to the other two, and carries two controls top-right: a direction toggle (proves the logical-properties discipline held — no CSS changes between LTR and RTL) and a motion toggle (the in-page control art-direction.md requires alongside the OS-level `prefers-reduced-motion`).

Fonts load from Google Fonts over the network, so this needs an internet connection — that is also why these are plain files rather than a published Artifact: an Artifact's CSP blocks the exact font request that is the point of this phase.

## Files

| File | Comp | Layout |
|---|---|---|
| [tokens.css](tokens.css) | — | The extraction. Every value phase 03 needs, and nothing that isn't used |
| [harness.css](harness.css) | — | Review-only chrome (the toggle buttons). Not art direction, not carried into phase 03 |
| [controls.js](controls.js) | — | Reveal/emphasize/parallax timing, the two toggles. Vanilla JS standing in for phase 04's Motion binding |
| [hero.html](hero.html) | Hero | `full-bleed` |
| [proof.html](proof.html) | Proof | `split-left` |
| [statement.html](statement.html) | Statement | `centered` |

## What I checked, mechanically

- **Contrast**, computed via the WCAG relative-luminance formula, not eyeballed: `--ink-faint` at the drafted 0.38 alpha failed 4.5:1 (3.28 on `--bg`, 3.36 on `--bg-elevated`) against the 13px eyebrow it colors — small text, not large text, so 4.5:1 is the real bar. Corrected to 0.50 (4.94 / 4.94). `--ink-muted` at 0.62 passed as drafted (7.14 / 6.73). `--accent` (#F4B740) passes at 11.09:1.
- **The display face's weights**, checked against what Google Fonts actually serves rather than assumed: `Instrument Serif` — the documented starting pairing — ships **only weight 400**. The tokens call for 500 at hero/section and 600 at stat; a 400-only face doesn't error on that request, it fakes a bold and the scale silently shifts, which is exactly the failure this phase's own checklist names. Swapped to **Fraunces** (SIL OFL, Fontsource, confirmed 400/500/600), same "confident serif" register, real weights.
- **RTL mirror** — verified live, toggling `dir` on the root with zero CSS changes. Grid auto-placement follows `direction` by default, so `split-left`'s DOM-first column (`.left`) lands on the visual right under RTL without a single override. One artifact worth knowing rather than fixing: the hero's trailing period visually jumps to the front of the line under `dir="rtl"` — correct Unicode bidi behavior for Latin text forced into an RTL container, and not representative of real RTL content, which would be RTL-script text throughout. Not a bug; not a v1 concern (v1 has no RTL).
- **Reduced motion** — the media query collapses every intent to opacity-only/200ms/no-transform at the token layer, so nothing downstream has to remember to check it. The in-page toggle does the same thing manually, live, for the OS-setting-shaped hole in the argument.
- **Every hand-written string checked against the schema caps** it will eventually cross (eyebrow ≤ 24, hero headline ≤ 60, section headline ≤ 60, body ≤ 240, stat label ≤ 40, quote ≤ 200) — all pass, and one stat label was trimmed to fit.
- **No one-off values.** Every number in the three comps traces to a named custom property in `tokens.css`; there is nothing in the markup that isn't a token reference.

## What I did not check, and should not have

The exit gate below has four items that are a human judgment call by design — this is, in the phase file's own words, "the one place AI assistance helps least." I built working comps to make that judgment possible; I did not make it. In particular, the reference board is a written list with specific pages, not saved images, and the "beautiful vs. over-designed" exercise below is my attempt at the prompt, offered as a starting point rather than a substitute for doing it yourself.

**Reference board** (Apple, Linear, Vercel are the doc's own starting direction — these are the specific pages, not the domains):

- Apple — any current product page (e.g. the MacBook Pro page): negative space at the hero, and how little text earns a lot of room
- Linear — linear.app marketing pages: hairline dividers, dark surface hierarchy, density without clutter
- Vercel — a recent launch/ship page: motion pacing, how a stat block earns its size rather than just being large
- Stripe — press/newsroom pages: restraint in a fintech context, proof that "serious" and "cinematic" aren't opposites

**Three beautiful, one over-designed** (my attempt, not the final word):
- Beautiful: Apple's product pages (restraint as the whole strategy), Linear's site (density that never feels busy), Arc browser's marketing site (motion with a point, not decoration)
- Over-designed: most Awwwards "site of the day" winners — technically impressive, and the content is always fighting the chrome for attention. `cinematic-dark` should read as closer to the first three than to this.

## Exit gate

- [x] Three comps exist as static HTML/CSS, authored in logical properties, against real copy
- [x] Reference board exists — as a written list above, not saved images (see caveat)
- [x] Type pairing chosen, open-licensed, confirmed to ship the weights specified — Fraunces (display) + Inter (text)
- [x] Extracted token list complete in `tokens.css`, no one-off numbers, no unused entries
- [x] Every contrast pair measured and passing
- [ ] **You would show the hero to someone** — open `hero.html` and decide. This is the actual gate.
