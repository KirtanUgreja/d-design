// The exit gate of docs/v1/plan/09-editor.md, as tests. Each block below maps
// to a heading in that file's Verify section.

import { describe, expect, it, beforeEach } from 'vitest';

import type { BlockPatch, Scene } from '@/schema';

import { CONTROLS, PRESENTATIONAL } from './controls';
import { applyPatch } from './patch';
import { useEditor } from './store';

const SCENES: Scene[] = [
  {
    id: 's1',
    intent: 'hook',
    layout: 'centered',
    blocks: [
      { id: 'b1', props: { type: 'headline', text: 'Ship the thing' } },
      { id: 'b2', props: { type: 'body', text: 'Most launches take too long.' } },
    ],
  },
  {
    id: 's2',
    intent: 'cta',
    layout: 'centered',
    blocks: [
      {
        id: 'b3',
        props: {
          type: 'cta',
          label: 'Start',
          href: 'https://example.com',
          style: 'primary',
        },
      },
    ],
  },
];

const patch = (over: Partial<BlockPatch> = {}): BlockPatch => ({
  sceneId: 's1',
  blockId: 'b1',
  props: { text: 'A better headline' },
  ...over,
});

// --- The patch ------------------------------------------------------------

describe('applyPatch', () => {
  it('changes only the target block, by identity not just by value', () => {
    const result = applyPatch(SCENES, patch());
    expect(result.ok).toBe(true);
    if (!result.ok) return;

    // Reference equality is a stronger claim than a deep compare: a deep
    // compare passes even when an untouched block was rebuilt identically,
    // and a rebuilt block is a re-render the performance rule forbids.
    expect(result.value[1]).toBe(SCENES[1]);
    expect(result.value[0]?.blocks[1]).toBe(SCENES[0]?.blocks[1]);
    expect(result.value[0]?.blocks[0]).not.toBe(SCENES[0]?.blocks[0]);
    expect(result.value[0]?.blocks[0]?.props).toMatchObject({
      type: 'headline',
      text: 'A better headline',
    });
  });

  it('leaves untouched blocks byte-identical, not merely deep-equal', () => {
    // Zod applies defaults on parse, so re-parsing a scene returns a tree in
    // which every block is a fresh object carrying `motion`/`region`/
    // `emphasis` defaults. Using that as the result would rebuild untouched
    // blocks on every keystroke and re-render the scene instead of the one
    // block (docs/coderules/performance.md, hot path 3). This asserts the
    // parse stayed a check rather than becoming the result.
    const result = applyPatch(SCENES, patch());
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    const untouched = result.value[0]?.blocks[1];
    expect(untouched).toBe(SCENES[0]?.blocks[1]);
    expect(untouched && 'motion' in untouched).toBe(false);
    expect(untouched && 'region' in untouched).toBe(false);
  });

  it('never mutates the tree it was given', () => {
    const before = structuredClone(SCENES);
    applyPatch(SCENES, patch());
    expect(SCENES).toEqual(before);
  });

  it('rejects a patch that would make the tree invalid, leaving it intact', () => {
    // 60 is `HeadlineProps.text`'s cap, straight off the Pydantic model.
    const result = applyPatch(SCENES, patch({ props: { text: 'x'.repeat(61) } }));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('invalid_input');
  });

  it('rejects an empty required string rather than accepting a blank headline', () => {
    expect(applyPatch(SCENES, patch({ props: { text: '' } })).ok).toBe(false);
  });

  it('rejects a javascript: href without asking the server', () => {
    // `CtaProps.href`'s allowlist is a `Field(pattern=...)` in Pydantic, so it
    // crossed the codegen boundary into Zod — which is the entire reason the
    // editor gets a generated validator rather than only types
    // (docs/coderules/typescript.md).
    const result = applyPatch(
      SCENES,
      patch({ sceneId: 's2', blockId: 'b3', props: { href: 'javascript:alert(1)' } }),
    );
    expect(result.ok).toBe(false);
  });

  it('refuses to change a block type, which is what keeps offline validation sound', () => {
    // The whole-tree rules — at most one Headline per scene, unique ids, a
    // region that exists on the layout — live in Pydantic and do not cross
    // into Zod. A props-only patch that cannot change `type` cannot reach any
    // of them, so this single refusal is what makes "a second Headline is
    // refused" true without a second copy of the rule in TypeScript.
    const result = applyPatch(
      SCENES,
      patch({ blockId: 'b2', props: { type: 'headline', text: 'Second headline' } }),
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.message).toContain('type');
  });

  it('reports a missing scene or block rather than throwing', () => {
    expect(applyPatch(SCENES, patch({ sceneId: 'nope' })).ok).toBe(false);
    expect(applyPatch(SCENES, patch({ blockId: 'nope' })).ok).toBe(false);
  });

  it('an AI edit and a panel edit of the same field produce the same patch', () => {
    // Both producers construct `{ sceneId, blockId, props }` — the AI's half
    // arrives as `EditResult.props`, the panel's is built from a control name
    // and a value. Same object, so the same code path applies it.
    const fromPanel: BlockPatch = {
      sceneId: 's1',
      blockId: 'b1',
      props: { text: 'Same' },
    };
    const fromModel: BlockPatch = {
      sceneId: 's1',
      blockId: 'b1',
      props: { text: 'Same' } as Record<string, unknown>,
    };
    expect(fromModel).toEqual(fromPanel);
    expect(applyPatch(SCENES, fromModel)).toEqual(applyPatch(SCENES, fromPanel));
  });
});

// --- Undo / redo ----------------------------------------------------------

describe('undo and redo', () => {
  beforeEach(() => useEditor.getState().reset(SCENES));

  it('undo restores the exact previous tree', () => {
    const store = useEditor.getState();
    store.patch(patch());
    expect(useEditor.getState().scenes).not.toEqual(SCENES);

    useEditor.getState().undo();
    expect(useEditor.getState().scenes).toEqual(SCENES);
  });

  it('redo after undo restores the next tree', () => {
    useEditor.getState().patch(patch());
    const edited = useEditor.getState().scenes;
    useEditor.getState().undo();
    useEditor.getState().redo();
    expect(useEditor.getState().scenes).toEqual(edited);
  });

  it('is one stack across both edit kinds, not two', () => {
    // The AI edit is applied by building the same BlockPatch, so it lands on
    // the same history. A user undoing does not have to know or care which
    // kind of edit they are undoing.
    useEditor.getState().patch(patch({ props: { text: 'From the panel' } }));
    useEditor.getState().patch(patch({ props: { text: 'From the model' } }));

    useEditor.getState().undo();
    expect(headline()).toBe('From the panel');
    useEditor.getState().undo();
    expect(headline()).toBe('Ship the thing');
  });

  it('a refused patch is not an undo step', () => {
    // Pressing undo after a rejected edit should return the last *successful*
    // change, not consume a step doing nothing.
    useEditor.getState().patch(patch({ props: { text: 'Good' } }));
    useEditor.getState().patch(patch({ props: { text: 'x'.repeat(61) } }));
    expect(useEditor.getState().error).not.toBeNull();
    expect(headline()).toBe('Good');

    useEditor.getState().undo();
    expect(headline()).toBe('Ship the thing');
  });

  it('a new edit forks the timeline and drops the redo branch', () => {
    useEditor.getState().patch(patch({ props: { text: 'First' } }));
    useEditor.getState().undo();
    useEditor.getState().patch(patch({ props: { text: 'Second' } }));
    useEditor.getState().redo();
    expect(headline()).toBe('Second');
  });

  it('undo at the beginning and redo at the end do nothing', () => {
    useEditor.getState().undo();
    expect(useEditor.getState().scenes).toEqual(SCENES);
    useEditor.getState().redo();
    expect(useEditor.getState().scenes).toEqual(SCENES);
  });
});

function headline(): unknown {
  const props = useEditor.getState().scenes[0]?.blocks[0]?.props;
  return props && 'text' in props ? props.text : undefined;
}

// --- The panel ------------------------------------------------------------

describe('the generated property panel', () => {
  it('offers no presentational control, for any block type', () => {
    // The no-styling invariant seen from the UI side. This is a test of the
    // *schema* wearing the panel's clothes: it fails the moment someone adds a
    // `fontSize` to a block, which is the moment it should.
    for (const [block, controls] of Object.entries(CONTROLS)) {
      for (const control of controls) {
        for (const word of PRESENTATIONAL) {
          expect(
            control.name.toLowerCase().includes(word),
            `${block}.${control.name} looks presentational`,
          ).toBe(false);
        }
      }
    }
  });

  it('covers every block type in the schema, with no list of its own', () => {
    expect(Object.keys(CONTROLS).sort()).toEqual([
      'abstract-visual',
      'body',
      'cta',
      'eyebrow',
      'headline',
      'image',
      'list',
      'quote',
      'slot',
      'stat',
      'video',
    ]);
  });

  it('derives controls from the schema, so a new prop needs no panel code', () => {
    // The evidence is that the caps and options here were never typed into
    // this repo's TypeScript: they come from `api/schema/scene.py` through the
    // generated Zod validator. Changing the Pydantic cap changes this test.
    expect(CONTROLS['eyebrow']).toEqual([
      { kind: 'text', name: 'text', maxLength: 24, multiline: false },
    ]);
    expect(CONTROLS['headline']).toContainEqual({
      kind: 'choice',
      name: 'emphasis',
      options: ['hero', 'section'],
      optional: true,
    });
  });

  it('makes the reroll seed a button, not a number field', () => {
    expect(CONTROLS['abstract-visual']).toContainEqual({ kind: 'reroll', name: 'seed' });
    expect(
      CONTROLS['abstract-visual']?.some((c) => c.name === 'seed' && c.kind === 'text'),
    ).toBe(false);
  });

  it('exposes description on a Slot and never its code', () => {
    const slot = CONTROLS['slot'] ?? [];
    expect(slot).toContainEqual({
      kind: 'text',
      name: 'description',
      maxLength: 200,
      multiline: true,
    });
    for (const name of ['html', 'css', 'js']) {
      expect(slot.find((c) => c.name === name)?.kind).toBe('readonly');
    }
  });

  it('never offers the block type or an asset id as a text field', () => {
    for (const controls of Object.values(CONTROLS)) {
      expect(controls.some((c) => c.name === 'type')).toBe(false);
      expect(controls.some((c) => c.name === 'assetId')).toBe(false);
    }
  });
});
