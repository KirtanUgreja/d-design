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
  switch (chart.chart_type) {
    case 'bar':
      return <BarChart chart={chart} />;
    case 'line':
      return <LineChart chart={chart} />;
    case 'donut':
      return <DonutChart chart={chart} />;
  }
}

/**
 * SVG chart primitives — the charts are drawn with the family's tokens, never
 * a value from the model (patterns.md rule 1). The model says *what* the chart
 * says; these components decide how it looks, using CSS custom properties that
 * the family registry sets. All colours are var() references or color-mix of
 * them — a chart carries no hex and no px from the AI output.
 */

const CHART_VIEWBOX = '0 0 480 280';

function useChartColors(): { ink: string; accent: string; faint: string } {
  // The tokens are consumed as CSS custom properties via the cascade; the SVG
  // needs concrete paint values, so they are read from the computed style of
  // the nearest .dds-deck. This is the renderer applying the family tokens —
  // the model never supplies a colour.
  return {
    ink: 'var(--dds-ink)',
    accent: 'var(--dds-accent)',
    faint: 'color-mix(in srgb, var(--dds-ink) 25%, transparent)',
  };
}

function BarChart({ chart }: { chart: ChartBlock }) {
  const { accent, faint } = useChartColors();
  const max = Math.max(...chart.series.map((s) => s.value), 1);
  const n = chart.series.length;
  const slot = 480 / n;
  const barWidth = Math.max(slot * 0.5, 12);
  return (
    <span className="dds-chart" data-chart="bar">
      <span className="dds-chart__title">{chart.title}</span>
      <svg viewBox={CHART_VIEWBOX} role="img" aria-label={chart.title}>
        {chart.series.map((s, i) => {
          const h = (s.value / max) * 220;
          const x = i * slot + (slot - barWidth) / 2;
          return (
            <g key={s.label}>
              <rect x={x} y={240 - h} width={barWidth} height={h} fill={accent} />
              <text x={x + barWidth / 2} y={264} textAnchor="middle" fontSize="12" fill={faint}>
                {s.label}
              </text>
            </g>
          );
        })}
      </svg>
    </span>
  );
}

function LineChart({ chart }: { chart: ChartBlock }) {
  const { ink, accent, faint } = useChartColors();
  const max = Math.max(...chart.series.map((s) => s.value), 1);
  const n = chart.series.length;
  const points = chart.series.map((s, i) => {
    const x = n === 1 ? 240 : (i / (n - 1)) * 440 + 20;
    const y = 240 - (s.value / max) * 200;
    return { x, y, label: s.label, value: s.value };
  });
  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
  return (
    <span className="dds-chart" data-chart="line">
      <span className="dds-chart__title">{chart.title}</span>
      <svg viewBox={CHART_VIEWBOX} role="img" aria-label={chart.title}>
        <path d={path} fill="none" stroke={ink} strokeWidth="3" />
        {points.map((p) => (
          <g key={p.label}>
            <circle cx={p.x} cy={p.y} r="5" fill={accent} />
            <text x={p.x} y={p.y - 12} textAnchor="middle" fontSize="12" fill={faint}>
              {p.label}
            </text>
          </g>
        ))}
      </svg>
    </span>
  );
}

function DonutChart({ chart }: { chart: ChartBlock }) {
  const { ink, accent, faint } = useChartColors();
  const total = chart.series.reduce((sum, s) => sum + s.value, 0) || 1;
  const first = chart.series[0];
  const cx = 240;
  const cy = 140;
  const r = 90;
  const circumference = 2 * Math.PI * r;
  let offset = 0;
  return (
    <span className="dds-chart" data-chart="donut">
      <span className="dds-chart__title">{chart.title}</span>
      <svg viewBox="0 0 480 280" role="img" aria-label={chart.title}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke={faint} strokeWidth="28" />
        {chart.series.map((s) => {
          const frac = s.value / total;
          const dash = frac * circumference;
          const el = (
            <circle
              key={s.label}
              cx={cx}
              cy={cy}
              r={r}
              fill="none"
              stroke={accent}
              strokeWidth="28"
              strokeDasharray={`${dash} ${circumference - dash}`}
              strokeDashoffset={-offset}
            />
          );
          offset += dash;
          return el;
        })}
        <text x={cx} y={cy - 6} textAnchor="middle" fontSize="28" fill={ink}>
          {first ? Math.round((first.value / total) * 100) : 0}
        </text>
        <text x={cx} y={cy + 18} textAnchor="middle" fontSize="12" fill={faint}>
          {first?.label ?? ''}
        </text>
      </svg>
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
