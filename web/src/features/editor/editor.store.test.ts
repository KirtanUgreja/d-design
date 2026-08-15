/**
 * Editor store tests — the undo/redo and re-skin guarantees (phase 12).
 *
 * Editing is local patches, no model call per keystroke; every mutator is
 * undoable. Undo/redo is the feature that makes AI editing safe to try, so
 * the stack behaviour is the thing tested: patch → undo restores, redo
 * re-applies, re-skin is undoable, and the family switcher never leaves the
 * registered set.
 */
import { describe, expect, it } from 'vitest';

import { createEditorStore } from './editor.store.js';
import { SAMPLE_DECK } from './sample-deck.js';

function firstSlideId(store: ReturnType<typeof createEditorStore>): string {
  const first = store.getState().deck.slides[0];
  if (!first) throw new Error('sample deck has slides');
  return first.id;
}

function firstBlock(store: ReturnType<typeof createEditorStore>) {
  const block = store.getState().deck.slides[0]?.blocks[0];
  if (!block || block.kind !== 'text') throw new Error('first block is text');
  return block;
}

describe('editor store', () => {
  it('patches copy locally and records history', () => {
    const store = createEditorStore(SAMPLE_DECK);
    store.getState().patchBlock(firstSlideId(store), 0, { content: 'A new headline' });
    expect(firstBlock(store).content).toBe('A new headline');
    expect(store.getState().past.length).toBe(1);
  });

  it('undo restores the pre-patch deck and redo re-applies it', () => {
    const store = createEditorStore(SAMPLE_DECK);
    const before = store.getState().deck;
    store.getState().patchBlock(firstSlideId(store), 0, { content: 'Edited' });
    store.getState().undo();
    expect(store.getState().deck).toEqual(before);
    store.getState().redo();
    expect(firstBlock(store).content).toBe('Edited');
    expect(store.getState().deck).not.toEqual(before);
  });

  it('re-skin changes the family and is undoable', () => {
    const store = createEditorStore(SAMPLE_DECK);
    const before = store.getState().deck;
    store.getState().setFamily('brutalist-stencil');
    expect(store.getState().deck.family_id).toBe('brutalist-stencil');
    // Content is untouched by re-skin.
    expect(store.getState().deck.slides).toEqual(before.slides);
    store.getState().undo();
    expect(store.getState().deck.family_id).toBe('editorial-serif');
  });

  it('rejects an unregistered family (the switcher never leaves the set)', () => {
    const store = createEditorStore(SAMPLE_DECK);
    store.getState().setFamily('does-not-exist');
    expect(store.getState().deck.family_id).toBe('editorial-serif');
    expect(store.getState().past.length).toBe(0);
  });

  it('reorders slides', () => {
    const store = createEditorStore(SAMPLE_DECK);
    const ids = store.getState().deck.slides.map((s) => s.id);
    store.getState().reorderSlide(0, 2);
    const reordered = store.getState().deck.slides.map((s) => s.id);
    expect(reordered[2]).toBe(ids[0]);
    expect(reordered[0]).toBe(ids[1]);
  });

  it('select and patchRegion work on the selected slide', () => {
    const store = createEditorStore(SAMPLE_DECK);
    const slideId = firstSlideId(store);
    store.getState().select(slideId);
    expect(store.getState().selection).toBe(slideId);
    store.getState().patchRegion(slideId, 0, 'primary');
    const region = store.getState().deck.slides[0]?.layout.regions[0];
    expect(region?.emphasis).toBe('primary');
    store.getState().select(null);
    expect(store.getState().selection).toBeNull();
  });
});
