// One scene: resolve blocks into regions, apply the shared scene padding
// shell (full-bleed opts out — it bleeds on purpose), layer the texture, and
// hand off to the layout that actually places blocks.

import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';
import type { Scene as SceneData } from '@/schema';

import { groupByRegion, SceneLayout } from './layouts';
import {
  SCENE_PADDING_BLOCK,
  SCENE_PADDING_INLINE,
  SCENE_PLACE,
  SCENE_SCROLL_MARGIN,
  sceneMinBlockVar,
  textureVar,
} from './tokens';

function Texture({ artDirection }: { artDirection: ArtDirection }) {
  const hasTexture = artDirection.texture.length > 0;
  if (!hasTexture) return null;
  return (
    <div
      style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}
      aria-hidden="true"
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `radial-gradient(ellipse at 50% 0%, var(--accent-soft), transparent 60%)`,
          opacity: textureVar('glow'),
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `radial-gradient(ellipse at center, transparent 40%, var(--bg) 100%)`,
          opacity: textureVar('vignette'),
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
          opacity: textureVar('grain'),
        }}
      />
    </div>
  );
}

export function Scene({
  scene,
  artDirection,
  motion,
}: {
  scene: SceneData;
  artDirection: ArtDirection;
  motion: MotionVocabulary;
}) {
  const blocksByRegion = groupByRegion(scene.blocks, scene.layout);
  const body = (
    <SceneLayout
      layout={scene.layout}
      blocksByRegion={blocksByRegion}
      artDirection={artDirection}
      motion={motion}
    />
  );

  return (
    // The id is what present/fullscreen.tsx's arrow-key navigation scrolls
    // to — a wrapper's concern, but it needs an anchor the core provides.
    //
    // The fit shell. Before this, a scene was exactly as tall as its padding
    // plus its content, so a four-word hero was ~40vh and a proof scene with a
    // list was ~130vh, and at every scroll position the viewport held the
    // bottom of one scene and the top of the next. Every compositional
    // judgement an art direction makes — negative space, where the eye lands,
    // whether a headline is the only thing on screen — assumes the scene owns
    // the frame, and it never did. docs/v2/plan/13-scene-fit.md.
    //
    // `min-block-size`, never `block-size`: the floor is a floor. A scene with
    // more content than the frame grows and gets reported; it is never clipped
    // and never scrolls inside itself. A fixed height plus `overflow: auto` is
    // how products arrive at an inner scrollbar by accident, and an inner
    // scrollbar inside a scrolling page is the worst outcome available here.
    //
    // Column flex rather than grid so that `justify-content` places the
    // content on the block axis while the item still stretches on the inline
    // axis. Grid's `place-content` would shrink the column to content width
    // and centre it, which quietly breaks every layout that expects the full
    // measure.
    <section
      id={`scene-${scene.id}`}
      style={{
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: SCENE_PLACE,
        minBlockSize: sceneMinBlockVar(scene.layout),
        // A property of a scene, so it lives in the core. The container-side
        // half — `scroll-snap-type` — is a property of a playback surface and
        // lives in `present/`, which is the rule-6 split for this phase.
        scrollSnapAlign: 'start',
        // Clears the fixed control pill that sits over the top of the frame.
        // Fixes `scrollIntoView` and the snap position in one declaration.
        scrollMarginBlockStart: SCENE_SCROLL_MARGIN,
      }}
    >
      <Texture artDirection={artDirection} />
      {scene.layout === 'full-bleed' ? (
        body
      ) : (
        <div
          style={{
            paddingInline: SCENE_PADDING_INLINE,
            paddingBlock: SCENE_PADDING_BLOCK,
          }}
        >
          {body}
        </div>
      )}
    </section>
  );
}
