// The editor's one store (docs/techstack/frontend.md -> "State: Zustand").
// One mutable document — the scene tree — plus selection, undo/redo, and the
// last error. Not a graph of atoms.
//
// Undo/redo is why a real store earns its place, and why it is built with the
// editor rather than after it: retrofitting undo into a store that mutates in
// place is a rewrite. It is what makes AI-assisted editing safe to *try*, and
// experimentation is where this product is fun.

import { create } from 'zustand';

import type { BlockPatch, Scene } from '@/schema';

import { applyPatch } from './patch';

export interface Selection {
  sceneId: string;
  blockId: string;
}

export interface EditorState {
  scenes: Scene[];
  selection: Selection | null;
  /** Set when a patch was refused. Cleared by the next successful one. */
  error: string | null;
  past: Scene[][];
  future: Scene[][];

  select: (selection: Selection | null) => void;
  patch: (patch: BlockPatch) => void;
  undo: () => void;
  redo: () => void;
  reset: (scenes: Scene[]) => void;
}

/** Depth is a memory bound, not a product decision — a tree is a few KB and
 * structural sharing means an undo entry costs one array plus the scenes that
 * actually changed. Deep enough that a user never finds the end of it during
 * a session, which is the only property that matters. */
const MAX_HISTORY = 100;

export const useEditor = create<EditorState>((set, get) => ({
  scenes: [],
  selection: null,
  error: null,
  past: [],
  future: [],

  select: (selection) => set({ selection }),

  patch: (patch) => {
    const { scenes, past } = get();
    const result = applyPatch(scenes, patch);
    if (!result.ok) {
      // The tree is untouched and the history is untouched. A refused edit is
      // not an undo step — a user pressing undo after a rejected patch expects
      // their last *successful* change back, not a no-op.
      set({ error: result.error.message });
      return;
    }
    set({
      scenes: result.value,
      past: [...past, scenes].slice(-MAX_HISTORY),
      // Any new edit forks the timeline; the redo branch is gone.
      future: [],
      error: null,
    });
  },

  undo: () => {
    const { past, future, scenes } = get();
    const previous = past.at(-1);
    if (!previous) return;
    set({
      scenes: previous,
      past: past.slice(0, -1),
      future: [scenes, ...future],
      error: null,
    });
  },

  redo: () => {
    const { past, future, scenes } = get();
    const next = future[0];
    if (!next) return;
    set({
      scenes: next,
      past: [...past, scenes],
      future: future.slice(1),
      error: null,
    });
  },

  // Loading a different experience is not an undoable action.
  reset: (scenes) => set({ scenes, selection: null, past: [], future: [], error: null }),
}));

/** The selected block, or null. A selector rather than a stored copy: a stored
 * copy is a second source of truth that goes stale the moment a patch lands. */
export function selectedBlock(state: EditorState) {
  if (!state.selection) return null;
  const scene = state.scenes.find((s) => s.id === state.selection?.sceneId);
  return scene?.blocks.find((b) => b.id === state.selection?.blockId) ?? null;
}
