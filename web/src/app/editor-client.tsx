'use client';

import { useMemo, useRef, useState } from 'react';

import {
  createEditorStore,
  DeckSwitcher,
  EditorCanvas,
  FamilySwitcher,
  GeneratePanel,
  PropertyPanel,
} from '../features/editor/index.js';
import type { BrandKit } from '../features/brand-kit/index.js';
import type { DeckSummary, SavedDeck } from '../features/decks/index.js';
import { SAMPLE_DECK } from '../features/editor/sample-deck.js';

export default function EditorClient({
  userId,
  kits = [],
  decks = [],
  plan = 'free',
}: {
  userId: string;
  kits?: BrandKit[];
  decks?: DeckSummary[];
  plan?: string;
}) {
  // The store is created once per mount from the sample deck; the ref keeps it
  // stable across re-renders (Zustand stores are created, not rendered).
  const storeRef = useRef<ReturnType<typeof createEditorStore> | null>(null);
  if (!storeRef.current) {
    storeRef.current = createEditorStore(SAMPLE_DECK);
  }
  const store = storeRef.current;

  const deck = store((s) => s.deck);
  const images = store((s) => s.images);
  const selection = store((s) => s.selection);
  const past = store((s) => s.past);
  const future = store((s) => s.future);

  // The saved deck this document belongs to, once it has one. Null means the
  // deck has never been saved — the first save creates, later ones update.
  const [deckId, setDeckId] = useState<string | null>(null);
  const [savedDecks, setSavedDecks] = useState<DeckSummary[]>(decks);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function refreshDecks() {
    const res = await fetch('/api/decks', { cache: 'no-store' });
    if (res.ok) {
      setSavedDecks((await res.json()) as DeckSummary[]);
    }
  }

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    try {
      const body = JSON.stringify({
        title: deck.slides[0]?.title ?? 'Untitled deck',
        deck,
        images,
      });
      const res = await fetch(deckId === null ? '/api/decks' : `/api/decks/${deckId}`, {
        method: deckId === null ? 'POST' : 'PUT',
        headers: { 'content-type': 'application/json' },
        body,
      });
      const data = (await res.json()) as { id?: string; error?: string };
      if (!res.ok) {
        throw new Error(data.error ?? 'save failed');
      }
      setDeckId(data.id ?? null);
      await refreshDecks();
    } catch (err) {
      setSaveError((err as Error).message ?? 'save failed');
    } finally {
      setSaving(false);
    }
  }

  async function handleLoad(id: string) {
    setSaveError(null);
    try {
      const res = await fetch(`/api/decks/${id}`, { cache: 'no-store' });
      const data = (await res.json()) as (SavedDeck & { error?: string }) | { error?: string };
      if (!res.ok) {
        throw new Error('error' in data && data.error ? data.error : 'load failed');
      }
      const saved = data as SavedDeck;
      // The images come back with the deck — reloading a generated deck must
      // not lose what the pipeline put in it.
      store.getState().loadDeck(saved.deck, saved.images);
      setDeckId(saved.id);
    } catch (err) {
      setSaveError((err as Error).message ?? 'load failed');
    }
  }

  const selectedIndex = useMemo(
    () => deck.slides.findIndex((s) => s.id === selection),
    [deck.slides, selection],
  );
  const selectedSlide = selectedIndex >= 0 ? deck.slides[selectedIndex] : undefined;

  async function handleLogout() {
    await fetch('/api/auth/sign-out', { method: 'POST' });
    window.location.href = '/login';
  }

  function handleExport() {
    // The editor edits the schema-shaped deck; the render pipeline is the only
    // HTML exporter (app.md: "the artefact is the single-file HTML, and it is
    // not hand-editable"). Downloading the deck JSON is the editable artefact;
    // feeding it to the render CLI produces the byte-identical HTML.
    const blob = new Blob([JSON.stringify(deck, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'deck.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  const [publishing, setPublishing] = useState(false);
  const [publishedUrl, setPublishedUrl] = useState<string | null>(null);
  const [publishError, setPublishError] = useState<string | null>(null);

  async function handlePublish() {
    setPublishing(true);
    setPublishError(null);
    try {
      const res = await fetch('/api/publish', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        // The image assets travel with the deck: the hosted page is the same
        // single file, and without them its image blocks render as placeholders.
        // The saved id travels too, so publishing updates the deck the editor is
        // working on instead of creating a second copy of it.
        body: JSON.stringify({
          deck,
          images,
          title: deck.slides[0]?.title ?? 'Deck',
          experienceId: deckId,
        }),
      });
      const data = (await res.json()) as {
        url?: string;
        error?: string;
        experienceId?: string;
      };
      if (!res.ok) {
        throw new Error(data.error ?? 'publish failed');
      }
      setPublishedUrl(data.url ?? null);
      // Publishing saves the deck as a side effect, so the editor now owns an
      // id it did not have before — the next Save updates rather than duplicating.
      if (data.experienceId !== undefined) {
        setDeckId(data.experienceId);
        void refreshDecks();
      }
    } catch (err) {
      setPublishError((err as Error).message ?? 'publish failed');
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div className="editor-layout">
      <div>
        <div className="editor-toolbar">
          <FamilySwitcher
            familyId={deck.family_id}
            onFamilyChange={(id) => store.getState().setFamily(id)}
          />
          <DeckSwitcher decks={savedDecks} onLoad={handleLoad} disabled={saving} />
          <div className="editor-toolbar__actions">
            <span className="editor-toolbar__user">{userId.slice(0, 8)}</span>
            <span className="editor-toolbar__plan" data-plan={plan}>
              {plan}
            </span>
            <button onClick={handleLogout}>Log out</button>
            {plan === 'paid' && (
              <a className="editor-toolbar__link" href="/brand-kits">
                Brand kits
              </a>
            )}
            <button onClick={() => store.getState().undo()} disabled={past.length === 0}>
              ↶ Undo
            </button>
            <button onClick={() => store.getState().redo()} disabled={future.length === 0}>
              ↷ Redo
            </button>
            <button className="editor-toolbar__export" onClick={handleExport}>
              Export
            </button>
            <button
              className="editor-toolbar__save"
              data-deck-id={deckId ?? 'unsaved'}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              className="editor-toolbar__publish"
              onClick={handlePublish}
              disabled={publishing}
            >
              {publishing ? 'Publishing…' : 'Publish'}
            </button>
          </div>
        </div>
        {saveError && <div className="editor-toolbar__error">{saveError}</div>}
        {publishedUrl && (
          <div className="editor-toolbar__published">
            Hosted:{' '}
            <a href={publishedUrl} target="_blank" rel="noreferrer">
              {publishedUrl}
            </a>
          </div>
        )}
        {publishError && <div className="editor-toolbar__error">{publishError}</div>}
        <GeneratePanel
          onGenerated={(built) => {
            store.getState().loadDeck(built.deck, built.images);
            // A generated deck is a new document: it has no saved id yet, so the
            // next Save creates rather than overwriting the deck that was open.
            setDeckId(null);
          }}
        />
        <EditorCanvas
          deck={deck}
          images={images}
          selection={selection}
          onSelect={(id) => store.getState().select(id)}
        />
      </div>
      {selectedSlide !== undefined && selectedIndex >= 0 ? (
        <PropertyPanel
          deck={deck}
          slide={selectedSlide}
          slideIndex={selectedIndex}
          slideCount={deck.slides.length}
          onPatchBlock={(blockIndex, content) =>
            store.getState().patchBlock(selectedSlide.id, blockIndex, { content })
          }
          onPatchRegion={(regionIndex, emphasis) =>
            store.getState().patchRegion(selectedSlide.id, regionIndex, emphasis)
          }
          onReorder={(from, to) => store.getState().reorderSlide(from, to)}
          kits={kits}
        />
      ) : (
        <aside className="editor-panel">
          <p className="editor-panel__note">
            Select a slide on the canvas to edit its copy, emphasis, and order.
          </p>
        </aside>
      )}
    </div>
  );
}
