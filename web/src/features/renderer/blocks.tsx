/**
 * Block renderers — how each block type becomes markup, styled only by the
 * design family's CSS custom properties.
 *
 * patterns.md rule 1 (the no-styling invariant) seen from this side: the model
 * emits *what* is on the slide; these components apply *how it looks* from the
 * family tokens. No hex, no px, no font name reaches here from the model.
 */

import type {
  ChartBlock,
  ImageBlock,
  QuoteBlock,
  Slide,
  StatBlock,
  TextBlock,
} from '../../schema/generated/Deck.js';
import type { MotionVocabulary } from '../design-system/index.js';

// The block union, derived from the schema (typescript.md: never hand-write a
// type that duplicates the generated one). Slide['blocks'][number] is the
// generated union.
export type SlideBlock = Slide['blocks'][number];

type BlockProps = {
  block: SlideBlock;
  motion: MotionVocabulary;
};

export function TextBlockView({ block, motion }: BlockProps) {
  const text = block as TextBlock;
  const cls = `dds-text dds-text--${text.style}`;
  return (
    <span className={cls} data-reveal={motion.reveal}>
      {text.content}
    </span>
  );
}

export function StatBlockView({ block }: BlockProps) {
  const stat = block as StatBlock;
  return (
    <span className="dds-stat">
      <span className="dds-stat__value">{stat.value}</span>
      <span className="dds-stat__label">{stat.label}</span>
    </span>
  );
}

export function QuoteBlockView({ block }: BlockProps) {
  const quote = block as QuoteBlock;
  return (
    <span className="dds-quote">
      <span className="dds-quote__text">{quote.text}</span>
      {quote.attribution && <span className="dds-quote__attr">— {quote.attribution}</span>}
    </span>
  );
}

export function ChartBlockView({ block }: BlockProps) {
  const chart = block as ChartBlock;
  const max = Math.max(...chart.series.map((s) => s.value), 1);
  return (
    <span className="dds-chart" data-chart={chart.chart_type}>
      <span className="dds-chart__title">{chart.title}</span>
      <span className="dds-chart__body">
        {chart.series.map((s) => (
          <span key={s.label} className="dds-chart__row">
            <span className="dds-chart__label">{s.label}</span>
            <span className="dds-chart__track">
              <span className="dds-chart__fill" style={{ width: `${(s.value / max) * 100}%` }} />
            </span>
          </span>
        ))}
      </span>
    </span>
  );
}

export function ImageBlockView({ block, motion, src }: BlockProps & { src?: string }) {
  const image = block as ImageBlock;
  const cls = `dds-image dds-image--${image.role}`;
  return (
    <span className={cls} data-reveal={motion.reveal}>
      {src ? (
        <img src={src} alt={image.alt} draggable={false} />
      ) : (
        <span className="dds-image__placeholder">{image.subject}</span>
      )}
    </span>
  );
}

export function BlockView(props: BlockProps & { src?: string }) {
  const { block } = props;
  switch (block.kind) {
    case 'text':
      return <TextBlockView {...props} />;
    case 'stat':
      return <StatBlockView {...props} />;
    case 'quote':
      return <QuoteBlockView {...props} />;
    case 'chart':
      return <ChartBlockView {...props} />;
    case 'image':
      return <ImageBlockView {...props} />;
  }
}
