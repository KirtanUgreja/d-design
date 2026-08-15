/**
 * The editor store — one mutable document with undo/redo (phase 12).
 *
 * frontend.md: the editor holds one mutable document — the deck tree — plus
 * selection, undo/redo, and in-flight patches. That is a single store, not a
 * graph of independent atoms, and Zustand fits it without a provider tree or
 * a reducer ceremony.
 *
 * Editing is local patches, no model call per keystroke (12-editor.md). Every
 * mutator produces a new deck immutably, pushes the pre-action deck onto
 * `past`, and clears `future`. Undo/redo is the feature that makes AI editing
 * safe to try.
 *
 * The store imports the Deck schema's public surface only — it never reaches
 * into the renderer (patterns.md rule 4, the feature boundary).
 */
import { create } from 'zustand';

import type { Deck, LayoutRegion, Slide, TextBlock } from '../../schema/generated/Deck.js';
import { DESIGN_FAMILY_TOKENS } from '../design-system/index.js';

export type EditorState = {
  deck: Deck;
  selection: string | null;
  past: Deck[];
  future: Deck[];

  patchSlide: (id: string, patch: Partial<Slide>) => void;
  patchBlock: (slideId: string, blockIndex: number, patch: Partial<TextBlock>) => void;
  patchRegion: (
    slideId: string,
    regionIndex: number,
    emphasis: NonNullable<LayoutRegion['emphasis']>,
  ) => void;
  reorderSlide: (from: number, to: number) => void;
  setFamily: (familyId: string) => void;
  select: (id: string | null) => void;
  undo: () => void;
  redo: () => void;
};

export function createEditorStore(initial: Deck) {
  return create<EditorState>()((set, get) => ({
    deck: initial,
    selection: null,
    past: [],
    future: [],

    patchSlide: (id, patch) => {
      const { deck } = get();
      const slides = deck.slides.map((s) => (s.id === id ? { ...s, ...patch } : s));
      commit(set, get, { ...deck, slides });
    },

    patchBlock: (slideId, blockIndex, patch) => {
      const { deck } = get();
      const slides = deck.slides.map((s) => {
        if (s.id !== slideId) return s;
        const blocks = s.blocks.map((b, i) =>
          i === blockIndex ? ({ ...b, ...patch } as TextBlock) : b,
        );
        return { ...s, blocks };
      });
      commit(set, get, { ...deck, slides });
    },

    patchRegion: (slideId, regionIndex, emphasis) => {
      const { deck } = get();
      const slides = deck.slides.map((s) => {
        if (s.id !== slideId) return s;
        const regions = s.layout.regions.map((r, i) =>
          i === regionIndex ? { ...r, emphasis } : r,
        );
        return { ...s, layout: { ...s.layout, regions } };
      });
      commit(set, get, { ...deck, slides });
    },

    reorderSlide: (from, to) => {
      const { deck } = get();
      const slides = [...deck.slides];
      const [moved] = slides.splice(from, 1);
      if (!moved) return;
      slides.splice(to, 0, moved);
      commit(set, get, { ...deck, slides });
    },

    setFamily: (familyId) => {
      if (!(familyId in DESIGN_FAMILY_TOKENS)) return;
      const { deck } = get();
      commit(set, get, { ...deck, family_id: familyId });
    },

    select: (id) => set({ selection: id }),

    undo: () => {
      const { past, future, deck } = get();
      const prev = past[past.length - 1];
      if (!prev) return;
      set({
        deck: prev,
        past: past.slice(0, -1),
        future: [deck, ...future],
      });
    },

    redo: () => {
      const { past, future, deck } = get();
      const next = future[0];
      if (!next) return;
      set({
        deck: next,
        past: [...past, deck],
        future: future.slice(1),
      });
    },
  }));
}

/** Push the pre-action deck onto the undo stack and apply the new one. */
function commit(set: (partial: Partial<EditorState>) => void, get: () => EditorState, next: Deck) {
  set({
    deck: next,
    past: [...get().past, get().deck],
    future: [],
  });
}
