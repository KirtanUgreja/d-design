'use client';

// The brand kit form (docs/v1/plan/10-brand-and-uploads.md -> "Brand kit").
//
// Cold 90% in almost every respect — assembled, not crafted. The one part that
// is not is `ContrastNotice`: "the contrast correction is visible to the user
// … silently deviating from a brand hex is worse than saying you did." A
// marketer who pastes their brand red and sees a different red on the page,
// with no explanation, concludes the product is broken or careless. Told why,
// they conclude it is careful.
//
// **Fonts are a select, and could not be anything else.** `FontId` is a
// Pydantic `Literal`, so the generated Zod is an enum and `BrandKit` has no
// representation for a family string. There is no text input to build here —
// which is the point, because a family name is echoed into a stylesheet and
// free text there is a CSS injection wearing a friendly label.

import {
  relativeLuminance,
  resolveBrand,
  toCssColor,
  type ArtDirection,
} from '@/features/art-direction';
import type { BrandKit } from '@/schema';

const FONTS = [
  { id: 'fraunces', label: 'Fraunces — serif, high contrast' },
  { id: 'inter', label: 'Inter — grotesque, neutral' },
] as const;

const LABEL = 'text-xs font-medium tracking-wide text-neutral-400 uppercase';
const INPUT =
  'w-full rounded-md border border-neutral-800 bg-neutral-950 px-2.5 py-1.5 text-sm ' +
  'text-neutral-100 focus:border-neutral-600 focus:outline-none';

export function BrandKitForm({
  kit,
  artDirections,
  onChange,
  onSave,
  saving,
  error,
}: {
  kit: BrandKit;
  /** Every art direction this account can publish under, resolved on the
   * server. The contrast notice below answers "here is what happens wherever
   * you publish this", which needs all of them — and since v2 phase 01 that is
   * a store read, so it cannot happen inside a client component. */
  artDirections: ArtDirection[];
  onChange: (kit: BrandKit) => void;
  onSave: () => void;
  saving: boolean;
  error: string | null;
}) {
  return (
    <section className="max-w-md space-y-5">
      <header>
        <h1 className="text-lg font-semibold text-neutral-100">Make this yours</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Your brand, applied to the art direction you already chose. Every page you
          generate from here uses it.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-3">
        <FontField
          label="Display font"
          value={kit.displayFont}
          onChange={(displayFont) => onChange({ ...kit, displayFont })}
        />
        <FontField
          label="Text font"
          value={kit.textFont}
          onChange={(textFont) => onChange({ ...kit, textFont })}
        />
      </div>

      <ColorField
        label="Primary"
        value={kit.primary}
        onChange={(primary) => onChange({ ...kit, primary })}
      />
      <ContrastNotice kit={kit} artDirections={artDirections} />

      <ColorField
        label="Secondary"
        value={kit.secondary}
        onChange={(secondary) => onChange({ ...kit, secondary })}
      />
      <ColorField
        label="Neutral"
        value={kit.neutral}
        onChange={(neutral) => onChange({ ...kit, neutral })}
      />

      {error && (
        <p role="alert" className="text-xs text-red-400">
          {error}
        </p>
      )}

      <button
        type="button"
        className="rounded-md bg-neutral-100 px-4 py-2 text-sm font-medium text-neutral-900 hover:bg-white disabled:opacity-40"
        onClick={onSave}
        disabled={saving}
      >
        {saving ? 'Saving…' : 'Save brand kit'}
      </button>
    </section>
  );
}

function FontField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: BrandKit['displayFont'];
  onChange: (value: BrandKit['displayFont']) => void;
}) {
  return (
    <label className="block">
      <span className={LABEL}>{label}</span>
      <select
        className={`${INPUT} mt-1.5`}
        value={value}
        aria-label={label}
        onChange={(e) => onChange(e.target.value as BrandKit['displayFont'])}
      >
        {FONTS.map((font) => (
          <option key={font.id} value={font.id}>
            {font.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function ColorField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="block">
      <span className={LABEL}>{label}</span>
      <div className="mt-1.5 flex items-center gap-2">
        <span
          aria-hidden
          className="h-8 w-8 shrink-0 rounded-md border border-neutral-700"
          style={{ background: value }}
        />
        <input
          className={INPUT}
          value={value}
          aria-label={label}
          onChange={(e) => onChange(e.target.value)}
        />
      </div>
    </label>
  );
}

/** The correction, said out loud — for every art direction, not just the one
 * this file used to import.
 *
 * `resolveBrand` corrects a primary that fails 4.5:1 against a given ground and
 * keeps the original for non-text surfaces; this makes that visible. It asked
 * `cinematic-dark` only, which was the whole story while there was one
 * direction and became a half-truth the moment there were two: a colour can
 * pass on near-black and fail on near-white, and the answer a brand kit owes
 * someone is "here is what happens wherever you publish this", not "here is
 * what happens if you pick the dark one".
 *
 * Three states per direction, and each is a different thing to tell someone:
 * their colour passed, their colour was adjusted for text and why, or their
 * colour cannot reach legibility at all — which fails closed rather than
 * shipping unreadable text.
 */
function ContrastNotice({
  kit,
  artDirections,
}: {
  kit: BrandKit;
  artDirections: ArtDirection[];
}) {
  return (
    <div className="space-y-2">
      {artDirections.map((artDirection) => (
        <ContrastNoticeFor key={artDirection.id} kit={kit} artDirection={artDirection} />
      ))}
    </div>
  );
}

function ContrastNoticeFor({
  kit,
  artDirection,
}: {
  kit: BrandKit;
  artDirection: ArtDirection;
}) {
  const id = artDirection.id;
  const resolved = resolveBrand(kit, artDirection);
  const ground = relativeLuminance(artDirection.color.bg) > 0.5 ? 'light' : 'dark';

  if (!resolved.ok) {
    return (
      <p className="rounded-md border border-amber-900/60 bg-amber-950/30 px-3 py-2 text-xs text-amber-200">
        <b className="font-medium">{id}</b> — that colour cannot be made legible on a{' '}
        {ground} background. Pick another primary; we would rather say so than ship text
        nobody can read.
      </p>
    );
  }

  const { accent, accentRaw } = resolved.value;
  // Compared as rendered values, not by reference. `resolveBrand` happens to
  // return the very same object when no correction was needed, so `===` would
  // work today — and would silently stop working the day it returns a copy.
  const corrected = toCssColor(accent);
  const yours = toCssColor(accentRaw);
  if (corrected === yours) {
    return (
      <p className="text-xs text-neutral-500">
        <b className="font-medium text-neutral-400">{id}</b> — passes on the {ground}{' '}
        background. Used exactly as you gave it.
      </p>
    );
  }

  return (
    <div className="space-y-1.5 rounded-md border border-neutral-800 bg-neutral-900/50 px-3 py-2">
      <p className="text-xs text-neutral-300">
        <b className="font-medium">{id}</b> — we adjusted your primary for text so it
        reaches 4.5:1 on the {ground} background. Your exact colour is still used for
        fills and glows.
      </p>
      <div className="flex items-center gap-3 text-xs text-neutral-500">
        <Swatch label="yours" color={yours} />
        <span aria-hidden>→</span>
        <Swatch label="for text" color={corrected} />
      </div>
    </div>
  );
}

function Swatch({ label, color }: { label: string; color: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span
        aria-hidden
        className="h-4 w-4 rounded border border-neutral-700"
        style={{ background: color }}
      />
      {label} <code className="text-neutral-400">{color}</code>
    </span>
  );
}
