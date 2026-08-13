/**
 * The design-system feature — the renderer's half of the design space.
 *
 * The Pydantic source of truth (api/schema/) holds the family identities and
 * the archetype catalogue; this feature holds the token values that bring them
 * to life, and the archetype catalogue mirror the mapping pass needs.
 */
export { DESIGN_FAMILY_TOKENS, familyTokens } from './tokens.js';
export type { DesignFamilySpec, DesignTokens, MotionVocabulary } from './tokens.js';
export { LAYOUT_ARCHETYPES, archetypeById } from './archetypes.js';
export type { LayoutArchetype } from './archetypes.js';
