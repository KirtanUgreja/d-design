/**
 * The design-system feature — the renderer's half of the design space.
 *
 * The Pydantic source of truth (api/schema/) holds the family identities and
 * the layout grammar; this feature holds the token values that bring them to
 * life. The renderer is grammar-driven (phase 10): it renders whatever
 * grammar-legal layout the Deck schema carries, so there is no catalogue
 * mirror here — the generated Deck types are the contract.
 */
export { DESIGN_FAMILY_TOKENS, familyTokens } from './tokens.js';
export type { DesignFamilySpec, DesignTokens, MotionVocabulary } from './tokens.js';
