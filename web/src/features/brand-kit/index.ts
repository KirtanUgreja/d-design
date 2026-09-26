/**
 * The brand-kit feature — the product surface for team-shared kits (phase 17).
 *
 * This is the client-side contract: the upload form's actions and the kit
 * types it renders. The heavy lifting (verification, re-encode, sanitize)
 * lives in the worker service; web's upload route forwards the file and
 * records the kit through api.
 */
export interface BrandKit {
  id: string;
  teamId: string;
  name: string;
  colors: Record<string, string>;
  logoRef: string | null;
  fontIds: string[];
}

export interface Team {
  id: string;
  name: string;
}

/** The api path prefix. api serves these routes with no `/api` prefix; the
 * reader (brand-kit.data.ts) is server-only and prefixes its own API_URL. */
export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? '/brand-kits';

export { BrandKitForm } from './brand-kit-form.js';
export type { BrandKitFormProps } from './brand-kit-form.js';
