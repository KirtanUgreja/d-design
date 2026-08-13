/**
 * Phase 00 — the design-system skeleton, seen from the renderer half.
 *
 * The renderer's token registry must mirror the family ids in
 * api/schema/design_families.py. A family id present on one side but not the
 * other is the drift the acceptance run's fingerprint check exists to catch.
 */
import { describe, expect, it } from 'vitest';

import { DESIGN_FAMILY_TOKENS, familyTokens } from '@web/features/design-system/index.js';

describe('design-system registry', () => {
  it('has at least ten families', () => {
    expect(Object.keys(DESIGN_FAMILY_TOKENS).length).toBeGreaterThanOrEqual(10);
  });

  it('keys every family by a non-empty id and gives it CSS tokens', () => {
    for (const spec of Object.values(DESIGN_FAMILY_TOKENS)) {
      expect(spec.id).toBeTruthy();
      expect(spec.tokens.id).toBe(spec.id);
      expect(Object.keys(spec.tokens.css).length).toBeGreaterThan(0);
    }
  });

  it('gives every family a motion vocabulary', () => {
    for (const spec of Object.values(DESIGN_FAMILY_TOKENS)) {
      expect(['fade', 'rise', 'slide', 'mask', 'none']).toContain(spec.motion.reveal);
      expect(['calm', 'steady', 'quick']).toContain(spec.motion.pacing);
    }
  });

  it('resolves families by id', () => {
    expect(familyTokens('swiss-grid')).toBeDefined();
    expect(familyTokens('does-not-exist')).toBeUndefined();
  });
});
