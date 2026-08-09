// The 11-way dispatch. One switch, one place that knows every block type —
// everything else in the tree only ever sees the `Block` union.

import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';
import type { Block } from '@/schema';

import { AbstractVisualBlock } from './abstract-visual';
import { BodyBlock } from './body';
import { CtaBlock } from './cta';
import { EyebrowBlock } from './eyebrow';
import { HeadlineBlock } from './headline';
import { ImageBlock } from './image';
import { ListBlock } from './list';
import { QuoteBlock } from './quote';
import { SlotBlock } from './slot';
import { StatBlock } from './stat';
import { VideoBlock } from './video';

export function BlockRenderer({
  block,
  artDirection,
  motion,
}: {
  block: Block;
  artDirection: ArtDirection;
  motion: MotionVocabulary;
}) {
  const props = block.props;
  switch (props.type) {
    case 'eyebrow':
      return <EyebrowBlock props={props} artDirection={artDirection} />;
    case 'headline':
      return <HeadlineBlock props={props} artDirection={artDirection} />;
    case 'body':
      return <BodyBlock props={props} artDirection={artDirection} />;
    case 'quote':
      return <QuoteBlock props={props} artDirection={artDirection} />;
    case 'list':
      return <ListBlock props={props} artDirection={artDirection} />;
    case 'stat':
      return <StatBlock props={props} artDirection={artDirection} motion={motion} />;
    case 'image':
      return <ImageBlock props={props} artDirection={artDirection} />;
    case 'video':
      return <VideoBlock props={props} artDirection={artDirection} />;
    case 'cta':
      return <CtaBlock props={props} artDirection={artDirection} />;
    case 'abstract-visual':
      return <AbstractVisualBlock props={props} />;
    case 'slot':
      return <SlotBlock props={props} artDirection={artDirection} />;
  }
}
