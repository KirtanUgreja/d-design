// One scene: resolve blocks into regions, apply the shared scene padding
// shell (full-bleed opts out — it bleeds on purpose), layer the texture, and
// hand off to the layout that actually places blocks.

import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';
import type { Scene as SceneData } from '@/schema';

import { groupByRegion, SceneLayout } from './layouts';
import { TextureLayerView } from './texture/texture-layer';
import {
  SCENE_PADDING_BLOCK,
  SCENE_PADDING_INLINE,
  SCENE_PLACE,
  SCENE_SCROLL_MARGIN,
  sceneMinBlockVar,
} from './tokens';

/** The art direction's layer list, in order. It used to be three hardcoded
 * `<div>`s — a radial-gradient glow, a radial-gradient vignette, and a grain —
 * which meant the texture *vocabulary* lived in the renderer and only its
 * opacities were tokens. Two of those three were gradients, and the glow was a
 * coloured bloom behind every hero: the artifact breaking our own principle 5,
 * which had been read as governing the chrome because of where it was filed.
 *
 * Now the renderer knows how to paint a kind and nothing about which kinds a
 * scene gets. docs/v2/plan/14-texture-without-gradient.md. */
function Texture({ artDirection }: { artDirection: ArtDirection }) {
  if (artDirection.texture.length === 0) return null;
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
        // **Ground, and it took a third art direction to notice it was not.**
        // A positioned element paints above its non-positioned siblings, and
        // the scene's content is in normal flow — so this layer has been on
        // *top* of the type since phase 14 built it. Nothing showed, because
        // the two art directions that existed set their loudest layer at 0.55
        // and 0.06 opacity: a film over the text is invisible when the film is
        // a film. `bold-brutalist` sets a `rule` layer at intensity 1 in full
        // ink, and it drew opaque black bars straight through the headline.
        //
        // Negative z-index puts it behind the flow, and `isolation: isolate` on
        // the section is what keeps "behind" from meaning "behind the page" —
        // without a stacking context there, this would escape the scene and
        // paint under the ground it is supposed to sit on.
        zIndex: -1,
      }}
      aria-hidden="true"
    >
      {artDirection.texture.map((layer, index) => (
        // Index as key: the list is a fixed, ordered composition from a token
        // file, not a collection that reorders. Position *is* the identity —
        // it is also what addresses the layer's custom properties.
        <TextureLayerView key={index} layer={layer} index={index} />
      ))}
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
        // Bounds the texture layer's negative z-index to this scene. See the
        // note in `Texture` — the two are one fix and neither works alone.
        isolation: 'isolate',
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
