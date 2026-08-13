/**
 * The layout-archetype catalogue — the renderer's mirror of
 * api/schema/archetypes.py. The mapping pass assigns archetypes by id; the
 * renderer frames them with the family's tokens. A model never invents a
 * layout — it picks from here.
 */

export type LayoutArchetype = {
  id: string;
  name: string;
  intent: string;
  variants: readonly string[];
};

export const LAYOUT_ARCHETYPES: readonly LayoutArchetype[] = [
  {
    id: 'opener',
    name: 'Opener',
    intent: 'Claim the topic with a single, unmissable statement.',
    variants: ['centered', 'split', 'frame'],
  },
  {
    id: 'statement',
    name: 'Statement',
    intent: 'One bold assertion, given room to land.',
    variants: ['centered', 'left', 'right'],
  },
  {
    id: 'section',
    name: 'Section break',
    intent: 'Mark a turn in the narrative and reset attention.',
    variants: ['centered', 'left', 'indexed'],
  },
  {
    id: 'split',
    name: 'Split',
    intent: 'Two ideas in tension, given equal weight.',
    variants: ['side-by-side', 'stacked', 'diagonal'],
  },
  {
    id: 'columns',
    name: 'Columns',
    intent: 'A set of peers: options, pillars, comparisons.',
    variants: ['two', 'three', 'four'],
  },
  {
    id: 'list',
    name: 'List',
    intent: 'A sequence of steps or principles, read in order.',
    variants: ['numbered', 'stacked', 'timeline'],
  },
  {
    id: 'stats',
    name: 'Stats',
    intent: 'Numbers as the argument.',
    variants: ['three', 'grid', 'banner'],
  },
  {
    id: 'quote',
    name: 'Quote',
    intent: 'A voice that is not the presenter.',
    variants: ['centered', 'pull', 'letterform'],
  },
  {
    id: 'image',
    name: 'Image',
    intent: 'One image carrying the meaning, with minimal type.',
    variants: ['full-bleed', 'frame', 'split'],
  },
  {
    id: 'callout',
    name: 'Callout',
    intent: 'One thing the audience must remember.',
    variants: ['banner', 'corner', 'centered'],
  },
  {
    id: 'quote-image',
    name: 'Quote + image',
    intent: 'A voice paired with a visual.',
    variants: ['side-by-side', 'overlay', 'split'],
  },
  {
    id: 'closer',
    name: 'Closer',
    intent: 'Land the deck: the ask, the next step, the final line.',
    variants: ['centered', 'split', 'full-bleed'],
  },
];

export function archetypeById(id: string): LayoutArchetype | undefined {
  return LAYOUT_ARCHETYPES.find((a) => a.id === id);
}
