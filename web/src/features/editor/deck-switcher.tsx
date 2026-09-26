/**
 * The deck switcher — reopening a saved deck.
 *
 * Mirrors `FamilySwitcher` deliberately: a native `<select>` over a list that
 * is small and known, because a custom popover would be chrome that competes
 * with the canvas (frontend.md — our chrome never does).
 *
 * It only loads. Saving is the toolbar's, because the save needs the live deck
 * and this component only knows which one was chosen.
 */
'use client';

import { useState } from 'react';

import type { DeckSummary } from '../decks/index.js';

export type DeckSwitcherProps = {
  decks: DeckSummary[];
  onLoad: (id: string) => void;
  disabled?: boolean;
};

export function DeckSwitcher({ decks, onLoad, disabled = false }: DeckSwitcherProps) {
  const [selected, setSelected] = useState('');

  // Nothing saved yet: the control would be a select with one useless option.
  if (decks.length === 0) {
    return null;
  }

  return (
    <div className="editor-deck-switcher">
      <select
        aria-label="Saved decks"
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
      >
        <option value="">Open a saved deck…</option>
        {decks.map((deck) => (
          <option key={deck.id} value={deck.id}>
            {deck.title}
            {deck.published_key === null ? '' : ' · published'}
          </option>
        ))}
      </select>
      <button onClick={() => onLoad(selected)} disabled={selected === '' || disabled}>
        Open
      </button>
    </div>
  );
}
