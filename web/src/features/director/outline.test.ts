import { describe, expect, it } from 'vitest';

import type { Outline } from '@/schema';

import {
  addScene,
  changeSceneIntent,
  deleteScene,
  moveScene,
  retitleOutline,
} from './outline';

const VALID: Outline = {
  title: 'A narrative',
  scenes: [
    { intent: 'hook', beat: 'open strong', layoutHint: 'centered' },
    { intent: 'problem', beat: 'name the pain', layoutHint: 'split-left' },
    { intent: 'proof', beat: 'show the evidence', layoutHint: 'grid' },
    { intent: 'cta', beat: 'ask for the click', layoutHint: 'centered' },
  ],
};

describe('moveScene', () => {
  it('reorders two non-hook scenes freely', () => {
    const result = moveScene(VALID, 1, 'down');
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.scenes.map((s) => s.intent)).toEqual([
        'hook',
        'proof',
        'problem',
        'cta',
      ]);
    }
  });

  it('refuses to drag a non-hook scene into first position', () => {
    const result = moveScene(VALID, 1, 'up');
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.code).toBe('invalid_input');
  });

  it('refuses to move past either end', () => {
    expect(moveScene(VALID, 0, 'up').ok).toBe(false);
    expect(moveScene(VALID, VALID.scenes.length - 1, 'down').ok).toBe(false);
  });
});

describe('deleteScene', () => {
  it('deletes a scene when the result is still a valid outline', () => {
    const withFive: Outline = {
      ...VALID,
      scenes: [
        ...VALID.scenes.slice(0, 2),
        { intent: 'reveal', beat: 'the twist', layoutHint: 'stack' },
        ...VALID.scenes.slice(2),
      ],
    };
    const result = deleteScene(withFive, 2);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.value.scenes).toHaveLength(4);
  });

  it('refuses to delete the only hook', () => {
    const result = deleteScene(VALID, 0);
    expect(result.ok).toBe(false);
  });

  it('refuses to delete the only cta', () => {
    const result = deleteScene(VALID, 3);
    expect(result.ok).toBe(false);
  });

  it('refuses to drop below 3 scenes', () => {
    const three: Outline = { ...VALID, scenes: VALID.scenes.slice(0, 3) };
    const result = deleteScene(three, 1);
    expect(result.ok).toBe(false);
  });
});

describe('changeSceneIntent', () => {
  it('refuses to create a second hook', () => {
    const result = changeSceneIntent(VALID, 1, 'hook');
    expect(result.ok).toBe(false);
  });

  it('refuses to move the hook off position 0 by changing its intent', () => {
    const result = changeSceneIntent(VALID, 0, 'problem');
    expect(result.ok).toBe(false);
  });

  it('refuses a change that creates adjacent repeats', () => {
    const result = changeSceneIntent(VALID, 1, 'proof');
    expect(result.ok).toBe(false);
  });

  it('allows a change that keeps the outline valid', () => {
    const result = changeSceneIntent(VALID, 2, 'reveal');
    expect(result.ok).toBe(true);
  });
});

describe('addScene', () => {
  it('inserts a scene when the result stays valid', () => {
    const result = addScene(VALID, 1, {
      intent: 'reveal',
      beat: 'a twist',
      layoutHint: 'stack',
    });
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.value.scenes).toHaveLength(5);
  });

  it('refuses an insert that creates adjacent repeats', () => {
    const result = addScene(VALID, 0, {
      intent: 'problem',
      beat: 'a second problem beat',
      layoutHint: 'stack',
    });
    expect(result.ok).toBe(false);
  });

  it('refuses to grow past 12 scenes', () => {
    const twelve: Outline = {
      ...VALID,
      scenes: [
        { intent: 'hook', beat: 'open strong', layoutHint: 'centered' },
        ...Array.from({ length: 10 }, (_, i): Outline['scenes'][number] => ({
          intent: i % 2 === 0 ? 'problem' : 'proof',
          beat: `beat ${i}`,
          layoutHint: 'stack',
        })),
        { intent: 'cta', beat: 'ask for the click', layoutHint: 'centered' },
      ],
    };
    expect(twelve.scenes).toHaveLength(12);
    const result = addScene(twelve, 0, {
      intent: 'reveal',
      beat: 'one too many',
      layoutHint: 'stack',
    });
    expect(result.ok).toBe(false);
  });
});

describe('retitleOutline', () => {
  it('replaces the title', () => {
    const result = retitleOutline(VALID, 'A better title');
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.value.title).toBe('A better title');
  });

  it('refuses an empty title', () => {
    const result = retitleOutline(VALID, '');
    expect(result.ok).toBe(false);
  });
});
