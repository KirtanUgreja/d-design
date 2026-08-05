// The outline-editor's edit operations (docs/v1/plan/07-director.md ->
// "The gate is the product decision"): reorder, delete, retitle, change
// intent, add. Every one returns a Result rather than mutating in place —
// "dragging a non-hook scene into first position is refused rather than
// silently rewriting intents" applies to all five, not only reordering.
//
// The generated `outlineSchema` (web/src/schema) is structural only —
// title length, scene count, each scene's own shape. Pydantic's pacing
// rules (exactly one hook, first; at least one cta; no adjacent repeat)
// live in a `@model_validator` method body, which has no JSON Schema
// representation, so they never reached Zod at all. This file is that
// logic's TypeScript side: needed for instant UI feedback during an edit
// (you cannot round-trip to the server per keystroke or per drag), with
// the server re-validating independently on submission regardless — the
// normal client-validates / server-is-still-the-source-of-truth split,
// not logic duplication of the schema itself.

import { err, ok, type Result } from '@/lib/result';
import { outlineSchema, type Outline } from '@/schema';

export type SceneIntent = Outline['scenes'][number]['intent'];
export type LayoutHint = NonNullable<Outline['scenes'][number]['layoutHint']>;
export type OutlineScene = Outline['scenes'][number];

// Zod's own copy of these two enums is buried behind
// ZodOptional -> ZodDefault -> ZodNullable -> ZodEnum internals not worth
// reaching into at runtime for six words each. Typed against the real
// union above so a typo'd or removed value is a compile error — that
// still leaves a real gap: adding a new enum value on the Python side
// updates the union but not this array, silently, and TypeScript has no
// way to flag "this list should list every member of that union." A
// values-of-a-union exhaustiveness check would close it; not worth the
// machinery for an enum docs/v1/scene-schema.md says rarely changes
// ("adding one is a real decision, not a convenience").
export const SCENE_INTENTS: SceneIntent[] = ['hook', 'problem', 'reveal', 'proof', 'cta'];
export const LAYOUT_HINTS: LayoutHint[] = [
  'full-bleed',
  'split-left',
  'split-right',
  'centered',
  'stack',
  'grid',
];

function validatePacing(outline: Outline): Result<Outline> {
  const hookIndexes = outline.scenes
    .map((s, i) => (s.intent === 'hook' ? i : -1))
    .filter((i) => i !== -1);
  if (hookIndexes.length !== 1 || hookIndexes[0] !== 0) {
    return err(
      'invalid_input',
      `exactly one scene has intent 'hook' and it is first; found at ${JSON.stringify(hookIndexes)}`,
    );
  }
  if (!outline.scenes.some((s) => s.intent === 'cta')) {
    return err('invalid_input', "an outline has at least one 'cta' scene");
  }
  for (let i = 0; i < outline.scenes.length - 1; i++) {
    const current = outline.scenes[i];
    const next = outline.scenes[i + 1];
    if (current === undefined || next === undefined) continue;
    if (current.intent === next.intent) {
      return err(
        'invalid_input',
        `adjacent scenes repeat intent '${current.intent}' at ${i}`,
      );
    }
  }
  return ok(outline);
}

/** Structural shape (Zod) then pacing rules (this file) — same order the
 * Python side checks them in, so the two never disagree about which rule
 * fired first. */
function validate(candidate: Outline): Result<Outline> {
  const parsed = outlineSchema.safeParse(candidate);
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return validatePacing(parsed.data);
}

export function moveScene(
  outline: Outline,
  index: number,
  direction: 'up' | 'down',
): Result<Outline> {
  const target = direction === 'up' ? index - 1 : index + 1;
  const current = outline.scenes[index];
  const swapWith = outline.scenes[target];
  if (
    target < 0 ||
    target >= outline.scenes.length ||
    current === undefined ||
    swapWith === undefined
  ) {
    return err('invalid_input', 'cannot move a scene past either end of the outline');
  }
  const scenes = [...outline.scenes];
  scenes[index] = swapWith;
  scenes[target] = current;
  return validate({ ...outline, scenes });
}

export function deleteScene(outline: Outline, index: number): Result<Outline> {
  const scenes = outline.scenes.filter((_, i) => i !== index);
  return validate({ ...outline, scenes });
}

export function retitleOutline(outline: Outline, title: string): Result<Outline> {
  return validate({ ...outline, title });
}

export function changeSceneIntent(
  outline: Outline,
  index: number,
  intent: SceneIntent,
): Result<Outline> {
  const scenes = outline.scenes.map((s, i) => (i === index ? { ...s, intent } : s));
  return validate({ ...outline, scenes });
}

export function changeLayoutHint(
  outline: Outline,
  index: number,
  layoutHint: LayoutHint | null,
): Result<Outline> {
  const scenes = outline.scenes.map((s, i) => (i === index ? { ...s, layoutHint } : s));
  return validate({ ...outline, scenes });
}

export function addScene(
  outline: Outline,
  afterIndex: number,
  scene: OutlineScene,
): Result<Outline> {
  const scenes = [
    ...outline.scenes.slice(0, afterIndex + 1),
    scene,
    ...outline.scenes.slice(afterIndex + 1),
  ];
  return validate({ ...outline, scenes });
}
