import type { LayoutProps } from './region';
import { RegionBlocks } from './region-blocks';
import { CONTENT_MAX, SCENE_PADDING_INLINE } from '../tokens';

export function FullBleedLayout({ blocksByRegion, artDirection, motion }: LayoutProps) {
  return (
    <div
      style={{
        position: 'relative',
        // Was a hardcoded 100vh min-block-size — a renderer constant deciding
        // a scene's frame, in the unit that overflows by the height of a
        // mobile URL bar.
        // It made full-bleed the one layout that owned the screen while the
        // other five were content-height, which is most of why the output read
        // as a long page with big gaps. The frame is now the fit shell's, from
        // the art direction's `fit` table (rule 20).
        //
        // `flexGrow` is how this layout says "I fill whatever frame I am
        // given" — bleeding to the edges and filling the frame are different
        // properties, and full-bleed opts out of the padding shell but not the
        // fit one. Under an art direction that answers `content` for this
        // layout there is no free space and this is inert, which is the right
        // way for it to degrade.
        flexGrow: 1,
        display: 'grid',
        placeItems: 'center',
      }}
    >
      <div style={{ position: 'absolute', inset: 0 }}>
        <RegionBlocks
          blocks={blocksByRegion.bg}
          artDirection={artDirection}
          motion={motion}
        />
      </div>
      <div
        style={{
          position: 'relative',
          zIndex: 1,
          maxInlineSize: CONTENT_MAX,
          paddingInline: SCENE_PADDING_INLINE,
          textAlign: 'center',
        }}
      >
        <RegionBlocks
          blocks={blocksByRegion.content}
          artDirection={artDirection}
          motion={motion}
          style={{ alignItems: 'center' }}
        />
      </div>
    </div>
  );
}
