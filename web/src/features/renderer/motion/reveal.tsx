'use client';

// The one motion wrapper every block uses. Progressive enhancement is not
// optional (docs/v1/plan/04-renderer.md): the resting state — fully visible,
// no transform — is what every process renders first, including the one with
// no JS. `armed` only flips true after mount, so hydration is what upgrades a
// finished page into an animated one, never the reverse.
//
// Reduced motion is not a branch in here. The wrapper that calls
// SceneRenderer chooses which MotionVocabulary to pass (CINEMATIC_MOTION vs
// REDUCED_MOTION); REDUCED_MOTION's distancePx/scale collapse every intent to
// an opacity fade, so this file only ever reads the vocabulary it's given.

import { motion, useInView, useScroll, useTransform } from 'motion/react';
import { useRef, useSyncExternalStore } from 'react';

import type { MotionIntent, MotionVocabulary } from '@/features/art-direction';

interface RevealProps {
  intent: MotionIntent;
  vocabulary: MotionVocabulary;
  delayMs: number;
  children: React.ReactNode;
  /** The block this wrapper belongs to, stamped on whichever element this
   * ends up rendering. Identity, not a mode: emitted unconditionally, the
   * same in all three processes, and carried by the published page too, so
   * rule 2 is untouched. The editor's selection overlay measures the box it
   * lands on — the alternative being the one the phase doc calls proof the
   * design is wrong, an overlay reaching into `renderer/blocks/`. */
  blockId?: string;
}

/** The resting state as plain CSS, for the unarmed render — the one every
 * process produces first, including the one with no JS. */
const REST_STYLE = { opacity: 1, transform: 'none' } as const;

/** The same resting state as a **Motion target**, which is a different thing
 * and has to be written differently.
 *
 * Motion animates its own transform props (`scale`, `x`, `y`) numerically; the
 * CSS `transform` shorthand is a string it cannot interpolate. Animating from
 * `transform: 'scale(0.96)'` to `transform: 'none'` therefore does not land on
 * the identity transform — it reads "none" as zero and lands on `scale(0)`,
 * collapsing the element to a 0×0 box that is still in the layout and still
 * has `opacity: 1`.
 *
 * Found in the v1 acceptance run, on the hero headline of the first experience
 * the product ever generated end to end: it faded in and then vanished. Every
 * block with `motion: 'emphasize'` did, in every process, including a
 * published page — the worst class of bug this renderer can have, since the
 * page looks fine until hydration finishes and then silently loses content.
 *
 * `reveal` survived the same mistake by luck: `translateY(Npx)` → "none"
 * degrades to `translateY(0)`, which is where it was going anyway. That is
 * also why nothing caught this — the reduced-motion e2e asserts on a `reveal`
 * block, the one intent whose bug is invisible. */
const REST_TARGET = { opacity: 1, scale: 1, y: 0 } as const;

const noopSubscribe = () => () => {};

/** True once hydrated, false on every process's first render (including the
 * one with no JS, which never runs the client snapshot at all). The
 * `useSyncExternalStore` server/client snapshot split is what upgrades the
 * page post-hydration without a `setState` in an effect. */
function useArmed(): boolean {
  return useSyncExternalStore(
    noopSubscribe,
    () => true,
    () => false,
  );
}

export function Reveal({ intent, vocabulary, delayMs, children, blockId }: RevealProps) {
  const armed = useArmed();

  if (intent === 'parallax') {
    return (
      <Parallax vocabulary={vocabulary} armed={armed} blockId={blockId}>
        {children}
      </Parallax>
    );
  }

  const def = vocabulary.intents[intent];
  if (!armed || intent === 'none') {
    return (
      <div style={REST_STYLE} data-block-id={blockId}>
        {children}
      </div>
    );
  }

  // Motion's own transform props, never the CSS shorthand — see REST_TARGET.
  // Both axes are named in both cases so the animation has a defined start and
  // end for each: an unmentioned prop is not animated, which is how a stale
  // transform from a previous intent would survive a re-render.
  const hidden =
    intent === 'emphasize'
      ? { opacity: 0, scale: def.scale, y: 0 }
      : { opacity: 0, scale: 1, y: def.distancePx };

  return (
    <motion.div
      data-block-id={blockId}
      initial={hidden}
      whileInView={REST_TARGET}
      viewport={{ once: true, amount: vocabulary.triggerRatio }}
      transition={{
        duration: def.durationMs / 1000,
        delay: delayMs / 1000,
        ease: def.ease,
      }}
    >
      {children}
    </motion.div>
  );
}

function Parallax({
  vocabulary,
  armed,
  children,
  blockId,
}: {
  vocabulary: MotionVocabulary;
  armed: boolean;
  children: React.ReactNode;
  blockId?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const distance = vocabulary.intents.parallax.distancePx;
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end start'],
  });
  const y = useTransform(scrollYProgress, [0, 1], [-distance, distance]);

  if (!armed || distance === 0) {
    return (
      <div ref={ref} style={REST_STYLE} data-block-id={blockId}>
        {children}
      </div>
    );
  }

  return (
    <motion.div ref={ref} style={{ y }} data-block-id={blockId}>
      {children}
    </motion.div>
  );
}

/** The Stat block's count-up trigger reuses the same visibility semantics as
 * Reveal rather than owning a second IntersectionObserver. */
export function useRevealTrigger(vocabulary: MotionVocabulary) {
  const ref = useRef<HTMLElement>(null);
  const inView = useInView(ref, { once: true, amount: vocabulary.triggerRatio });
  return { ref, inView };
}
