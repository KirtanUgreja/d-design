'use client';

// `value` is a string, not a number (docs/v1/scene-schema.md). Only a value
// that parses as a plain number counts up — "10x", "2.4M", "<50ms" all fail
// the numeric test on purpose and hold static, exactly as the schema doc
// specifies. Formatting goes through `Intl` (patterns.md rule 7): never
// string concatenation, which is also the XSS boundary for this block.

import { useEffect, useState } from 'react';

import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';

import type { StatProps } from './block-props';
import { typeStyle } from '../tokens';
import { useRevealTrigger } from '../motion/reveal';

const NUMERIC = /^-?\d+(\.\d+)?$/;

function decimalsOf(value: string): number {
  const dot = value.indexOf('.');
  return dot === -1 ? 0 : value.length - dot - 1;
}

function useCountUp(target: number, active: boolean, durationMs: number): number {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!active) return;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / durationMs);
      setValue(target * (1 - (1 - t) ** 3));
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, target, durationMs]);
  return value;
}

export function StatBlock({
  props,
  artDirection,
  motion: vocabulary,
}: {
  props: StatProps;
  artDirection: ArtDirection;
  motion: MotionVocabulary;
}) {
  const { ref, inView } = useRevealTrigger(vocabulary);
  const numeric = NUMERIC.test(props.value.trim())
    ? Number.parseFloat(props.value)
    : null;
  const decimals = numeric === null ? 0 : decimalsOf(props.value.trim());
  const animated = useCountUp(
    numeric ?? 0,
    inView && numeric !== null,
    vocabulary.intents.reveal.durationMs,
  );

  const display =
    numeric === null
      ? props.value
      : new Intl.NumberFormat(undefined, {
          minimumFractionDigits: decimals,
          maximumFractionDigits: decimals,
        }).format(animated);

  return (
    <div ref={ref as React.RefObject<HTMLDivElement>}>
      <div style={typeStyle('stat', artDirection)}>
        {props.prefix}
        {display}
        {props.suffix}
      </div>
      <div style={typeStyle('muted', artDirection)}>{props.label}</div>
    </div>
  );
}
