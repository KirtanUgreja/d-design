// The property panel, derived from the schema rather than written eleven times
// (docs/v1/plan/09-editor.md -> "The panel is generated, not written").
//
// Eleven hand-written panels is eleven places for a new prop to be forgotten,
// and it is precisely the duplication shape docs/coderules/ai-authorship.md
// measures. Deriving them means adding a prop to the Pydantic model makes the
// control appear with no panel code touched — asserted in `editor.test.ts`.
//
// The consequence is the one that matters: because no prop in the schema is
// presentational, **the panel is structurally incapable of offering a font
// size or a colour picker**. Not hidden, not disabled — unrepresentable. The
// thing users most expect and most reliably use to wreck a design cannot be
// built here, and not because someone remembered to leave it out.

import { z } from 'zod';

import { blockSchema } from '@/schema';

export type Control =
  | { kind: 'text'; name: string; maxLength: number | null; multiline: boolean }
  | { kind: 'choice'; name: string; options: string[]; optional: boolean }
  | { kind: 'boolean'; name: string }
  | { kind: 'reroll'; name: string }
  /** A prop the panel knows exists and deliberately does not edit — `Slot`'s
   * `html`/`css`/`js`. Rendered as a read-only note, never as a field. */
  | { kind: 'readonly'; name: string };

/** Props that are identity or structure rather than content. `type` is the
 * discriminator and holding it immutable is what keeps whole-tree validation
 * sound offline (see `patch.ts`); `assetId`/`posterAssetId` are swapped through
 * the asset picker that arrives with phase 10, not typed into a box. */
const NOT_EDITABLE_HERE = new Set(['type', 'assetId', 'posterAssetId']);

/** `Slot`'s code is not hand-editable in v1 — the panel exposes `description`
 * only, and an AI edit operates on the description. Hand-editing sandboxed
 * code is a feature for a different product. */
const SLOT_CODE = new Set(['html', 'css', 'js']);

/** Long enough that a single-line input would be the wrong shape. */
const MULTILINE_OVER = 80;

/** Every block type's controls, keyed by the `type` discriminator. Built once
 * at module load by walking the generated Zod union — there is no list of
 * block types in this file, and that absence is the feature. */
export const CONTROLS: Record<string, Control[]> = buildControls();

function buildControls(): Record<string, Control[]> {
  const out: Record<string, Control[]> = {};
  const props = blockSchema.shape.props;
  for (const variant of props.options) {
    const shape = variant.shape;
    const literal = shape['type'];
    const name = literalValue(literal);
    if (name === null) continue;
    out[name] = Object.entries(shape)
      .filter(([key]) => !NOT_EDITABLE_HERE.has(key))
      .map(([key, schema]) => toControl(name, key, schema))
      .filter((c): c is Control => c !== null);
  }
  return out;
}

function toControl(block: string, name: string, schema: z.ZodType): Control | null {
  if (SLOT_CODE.has(name)) return { kind: 'readonly', name };

  // The one affordance users reach for constantly, and the reason it is a
  // button: a seed is a number with no meaning, so a number field invites
  // someone to reason about a value that cannot be reasoned about. "Reroll" is
  // the same action with the arithmetic removed.
  if (block === 'abstract-visual' && name === 'seed') return { kind: 'reroll', name };

  const { inner, optional } = unwrap(schema);

  if (inner instanceof z.ZodEnum) {
    return {
      kind: 'choice',
      name,
      options: Object.values(inner.enum) as string[],
      optional,
    };
  }
  if (inner instanceof z.ZodBoolean) return { kind: 'boolean', name };
  if (inner instanceof z.ZodString) {
    const maxLength = inner.maxLength;
    return {
      kind: 'text',
      name,
      maxLength,
      multiline: maxLength !== null && maxLength > MULTILINE_OVER,
    };
  }

  // Arrays and objects — `List.items` is the only one in v1. Editing a
  // repeated sub-object is its own interaction, and inventing a generic one
  // here would be a worse version of the thing phase 11 will need anyway.
  return null;
}

/** Peel `.nullable().default().optional()` off a generated field to reach the
 * type that decides which control it gets. The generated schema wraps every
 * Pydantic field with a default in exactly this way, so this is reading the
 * emitter's own convention rather than guessing at Zod internals. */
function unwrap(schema: z.ZodType): { inner: z.ZodType; optional: boolean } {
  let inner = schema;
  let optional = false;
  for (;;) {
    if (inner instanceof z.ZodOptional) {
      optional = true;
      inner = inner.unwrap() as z.ZodType;
    } else if (inner instanceof z.ZodNullable) {
      optional = true;
      inner = inner.unwrap() as z.ZodType;
    } else if (inner instanceof z.ZodDefault) {
      optional = true;
      inner = inner.def.innerType as z.ZodType;
    } else {
      return { inner, optional };
    }
  }
}

function literalValue(schema: z.ZodType | undefined): string | null {
  if (!(schema instanceof z.ZodLiteral)) return null;
  const [value] = schema.values;
  return typeof value === 'string' ? value : null;
}

/** Words that would name a presentational control if one could exist. The
 * no-styling invariant seen from the UI side: `editor.test.ts` walks every
 * generated control and asserts none of these appears, which is a test of the
 * *schema* wearing the panel's clothes. It fails the moment someone adds a
 * `fontSize` to a block, which is the moment it should. */
export const PRESENTATIONAL = [
  'color',
  'colour',
  'font',
  'size',
  'px',
  'rem',
  'duration',
  'ease',
  'easing',
  'weight',
  'spacing',
  'margin',
  'padding',
  'radius',
  'shadow',
  'opacity',
] as const;

// Not in the list, on purpose: `width` and `height`. `Slot.height` is
// `'viewport' | 'auto'` — a semantic choice with no measurement in it, which
// is exactly the distinction rule 7 draws. The rule bans presentational
// *values* (a hex, a px, a font name, a duration), not nouns; a list that
// flagged `height` would be enforcing a spelling convention rather than the
// invariant, and would fail on a schema that is entirely correct.
