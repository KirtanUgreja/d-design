/**
 * renderer — the pure, mode-free renderer core.
 *
 * The single source of visual truth on the TypeScript side. Consumes the Deck
 * schema and the design-family tokens; never knows whether it is being
 * rendered for an editor, an export, or a present shell (patterns.md rule 2).
 */
export { DeckRenderer } from './deck-renderer.js';
export type { DeckRendererProps } from './deck-renderer.js';
export { SlideRenderer } from './slide-renderer.js';
export type { SlideRendererProps } from './slide-renderer.js';
export { BlockView } from './blocks.js';
