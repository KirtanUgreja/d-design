'use client';

import { useMemo, useRef, useState } from 'react';

import {
  createEditorStore,
  EditorCanvas,
  FamilySwitcher,
  PropertyPanel,
} from '../features/editor/index.js';
import type { BrandKit } from '../features/brand-kit/index.js';
import { SAMPLE_DECK } from '../features/editor/sample-deck.js';

export default function EditorClient({
  userId,
  kits = [],
  plan = 'free',
}: {
  userId: string;
  kits?: BrandKit[];
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
  const selection = store((s) => s.selection);
  const past = store((s) => s.past);
  const future = store((s) => s.future);

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
        body: JSON.stringify({ deck, title: deck.slides[0]?.title ?? 'Deck' }),
      });
      const data = (await res.json()) as { url?: string; error?: string };
      if (!res.ok) {
        throw new Error(data.error ?? 'publish failed');
      }
      setPublishedUrl(data.url ?? null);
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
          <div className="editor-toolbar__actions">
            <span className="editor-toolbar__user">{userId.slice(0, 8)}</span>
            <span className="editor-toolbar__plan" data-plan={plan}>
              {plan}
            </span>
            <button onClick={handleLogout}>Log out</button>
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
              className="editor-toolbar__publish"
              onClick={handlePublish}
              disabled={publishing}
            >
              {publishing ? 'Publishing…' : 'Publish'}
            </button>
          </div>
        </div>
        {publishedUrl && (
          <div className="editor-toolbar__published">
            Hosted:{' '}
            <a href={publishedUrl} target="_blank" rel="noreferrer">
              {publishedUrl}
            </a>
          </div>
        )}
        {publishError && <div className="editor-toolbar__error">{publishError}</div>}
        <EditorCanvas
          deck={deck}
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
