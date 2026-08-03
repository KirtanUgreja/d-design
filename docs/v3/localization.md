# Localization

One experience, twelve languages, and the design never breaks.

The most underrated feature in v3: enormous real value for product launches, deeply AI-native, and technically low-risk compared to 3D or analytics.

## Transcreation, not translation

Translation produces text of arbitrary length. German runs ~35% longer than English, Japanese ~40% shorter. A headline that fits `bold-brutalist`'s 34-character budget in English becomes 46 characters in German, and every locale lights up the v2 overflow banner.

So the system does not translate and then fix. **It translates within the budget.**

> *"Express this headline in German, in under 34 characters, in this tone."*

This is what a human localizer does, and it is only possible because per-AD character budgets exist. v2's budget system — introduced to make reskin safe — turns out to be the thing that makes localization work. That is the abstraction paying off.

The layout never breaks, in any language, in any art direction.

### Consequence: locale trees are real

```
locales  experience_id, locale, direction, scenes (jsonb), published_at, status
```

Each locale gets its own scene tree, transcreated at publish. Not a string table applied at render — the copy genuinely differs, because fitting a budget in Japanese means different phrasing, not a translated string.

Structure is identical across locales: same scenes, same blocks, same ids. Only text props change. This keeps reskin, personalization, and editing working uniformly, and it means a structural edit propagates while a copy edit does not.

## Quality — the honest problem

**The AI will produce confident, budget-fitting, subtly wrong German, and you will not catch it.**

This is the real risk of the feature. A tool that silently damages the brands it serves in languages the operator cannot read is worse than no localization at all.

Mitigation, non-optional:

- Every locale starts at `status: 'needs-review'`
- Publishing a locale requires an explicit human confirmation
- Side-by-side source/target review, per block, with the character budget visible
- Any edited block is marked reviewed; unreviewed locales carry a visible state in the editor

Ship the review path in the same release as the transcreation. A locale that publishes without review is the failure mode.

### The review gate is also the compliance gate

EU AI Act guidance names **AI-manipulated translations** explicitly among the content that must be marked machine-readably as artificially generated. Transcreation is not a mechanical translation — it is a rewrite to fit a character budget, which materially affects meaning by the guidance's own wording.

So the `needs-review` workflow above is doing two jobs at once: it catches subtly wrong German, and it is the human oversight step that makes each locale's AI-generated status a reviewed fact. Each locale page carries its own marking, independent of the source. See [compliance.md](compliance.md).

## Per-script fonts

Your display font almost certainly has no Japanese, Arabic, or Cyrillic. Without fallbacks, the feature looks broken outside Latin — and it looks broken in a way that reads as carelessness.

Each AD declares stacks per script:

```ts
type.scripts: {
  latin:    { display, text }
  cjk:      { display, text }
  arabic:   { display, text }
  cyrillic: { display, text }
}
```

Fallbacks are chosen to preserve *character*, not to match shapes. `bold-brutalist` needs a CJK face with comparable weight and density; `editorial-light` needs one with comparable restraint. A neutral system font in every non-Latin script silently flattens all three ADs into the same design.

Per-script metric adjustments come with it — CJK type generally needs slightly looser line height and no negative tracking, which means `type.scripts` carries scale overrides, not only families.

## RTL — mostly free, if the renderer was authored correctly

Arabic and Hebrew mirror the entire experience. The amount of work that takes was decided back in v1, by whether the renderer used physical or logical CSS properties.

**Author everything in CSS logical properties from the start.** `margin-inline-start` instead of `margin-left`, `padding-block-end` instead of `padding-bottom`, `inline-size`/`block-size` instead of `width`/`height`, `border-inline-start` instead of `border-left`. Set `dir` on the root and the entire layout flips with no separate stylesheet, no mirrored token set, and no per-component branching.

This is a **v1 decision with a v3 payoff**, and the asymmetry is brutal: authored logically from day one, RTL costs almost nothing. Authored physically and retrofitted, it means auditing every one of the 19 primitives across 3 art directions.

### What logical properties handle automatically

| | |
|---|---|
| Layouts | `split-left` / `split-right` flip on their own — the names describe *authoring* position, and the renderer resolves reading order |
| Spacing, borders, radii | All of it, given logical authoring |
| Text alignment and flow | Automatic |
| Grid and flex flow | Follows `direction` |

### What does not, and must be handled explicitly

**`transform` is the documented exception** — it operates on x/y axes and ignores block/inline entirely. That is precisely where this product lives:

- **`revealX` / any `translateX` in the motion vocabulary** must invert manually in RTL. The reveal that slides in from the left in English must slide from the right in Arabic, and no logical property will do it for you.
- **`Marquee` direction** inverts.
- **`Timeline`** in horizontal orientation reverses; vertical is unaffected.
- **Parallax** is `translateY` — unchanged.

That is the whole exception list, and it is short enough to test exhaustively.

`direction` is a property of the locale, not the scene tree. The renderer resolves it, so nothing in the IR changes and a single tree serves both directions.

Logos, product photography, and 3D scenes do **not** mirror. Only layout and reading order do.

## Delivery

```
/e/[id]           canonical, source locale
/e/[id]/es        Spanish
/e/[id]/de        German
```

Locale-prefixed URLs are the foundation. Each is a real, shareable, indexable page with `hreflang` tags and its own OG metadata.

Auto-detect sits **on top**: a first-time visitor with `Accept-Language: de` is redirected to `/de`, and an explicit choice is remembered and always wins. Auto-detect alone cannot work — it has to redirect somewhere, and without locale URLs there is nothing to redirect to, nothing to share, and nothing to index.

An on-page language switcher is always present. Auto-detection is a guess, and guesses need an escape hatch.

## Interaction with everything else

| | Behavior |
|---|---|
| **Reskin** | Reskinning re-runs transcreation against the new AD's budgets — Japanese for `editorial-light` (80) differs from `bold-brutalist` (34). Locales return to `needs-review` |
| **Personalization** | Fields substitute per locale; `company` is not translated |
| **Live data** | Numbers format per locale — separators, currency, date order |
| **Slides mode** | Uses the same tree; overflow recomputed per locale |

The reskin row is the expensive one. Changing art direction on a 12-locale experience means 12 transcreation passes and 12 reviews. Warn before, not after.

## Verification

- 5 experiences × 12 locales × 3 ADs → zero budget overflows
- Native-speaker review on at least 3 locales before claiming the feature works
- Arabic renders fully mirrored: splits swapped, motion reversed, marquee reversed
- CJK renders in each AD's declared face, not a system fallback
- `hreflang` present and correct on every locale page
- Explicit language choice survives reload and beats auto-detect
