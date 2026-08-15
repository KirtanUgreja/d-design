/**
 * The re-skin switcher — the abstraction claim demonstrated (phase 12).
 *
 * app.md: "reserve the design-family switcher's space now — v2 fills it."
 * Switching the deck's design family changes the whole look in seconds, with
 * the content untouched. This is the strongest proof that the design system
 * is a layer, not a theme.
 */
'use client';

import { DESIGN_FAMILY_TOKENS } from '../design-system/index.js';

export type FamilySwitcherProps = {
  familyId: string;
  onFamilyChange: (familyId: string) => void;
};

export function FamilySwitcher({ familyId, onFamilyChange }: FamilySwitcherProps) {
  return (
    <label className="editor-family-switcher">
      <span>Design family</span>
      <select value={familyId} onChange={(e) => onFamilyChange(e.target.value)}>
        {Object.keys(DESIGN_FAMILY_TOKENS).map((id) => (
          <option key={id} value={id}>
            {id}
          </option>
        ))}
      </select>
    </label>
  );
}
