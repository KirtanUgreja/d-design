// One scene: resolve blocks into regions, apply the shared scene padding
// shell (full-bleed opts out — it bleeds on purpose), layer the texture, and
// hand off to the layout that actually places blocks.

import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';
import type { Scene as SceneData } from '@/schema';

import { groupByRegion, SceneLayout } from './layouts';
import { SCENE_PADDING_BLOCK, SCENE_PADDING_INLINE, textureVar } from './tokens';

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
    <section id={`scene-${scene.id}`} style={{ position: 'relative' }}>
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
