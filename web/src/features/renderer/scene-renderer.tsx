// The signature is the contract (docs/v1/plan/04-renderer.md). Nothing else:
// no `mode`, no `process.env`, no `typeof window`, no branch on where it is
// running. It runs in the browser, the app server, and (from v2) the job
// worker, and must behave identically in all three — patterns.md rule 2.

import type { CSSProperties } from 'react';

import type { ArtDirection, MotionVocabulary } from '@/features/art-direction';
import { toCssVars } from '@/features/art-direction';
import type { Scene as SceneData } from '@/schema';

import { Scene } from './scene';
import { COLOR_VAR } from './tokens';

export interface SceneRendererProps {
  scenes: SceneData[];
  artDirection: ArtDirection;
  motion: MotionVocabulary;
}

export function SceneRenderer({ scenes, artDirection, motion }: SceneRendererProps) {
  const vars = toCssVars(artDirection);
  return (
    <div
      style={
        {
          ...vars,
          background: COLOR_VAR.bg,
          color: COLOR_VAR.ink,
        } as CSSProperties
      }
    >
      {scenes.map((scene) => (
        <Scene key={scene.id} scene={scene} artDirection={artDirection} motion={motion} />
      ))}
    </div>
  );
}
