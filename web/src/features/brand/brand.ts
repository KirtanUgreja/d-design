// The brand kit's client. Two calls, and a `not_found` that is a normal state
// rather than an error: the brand kit is asked for *second*, after the first
// artifact exists (docs/v1/plan/10-brand-and-uploads.md), so a new user
// legitimately has none.

import { err, ok, type Result } from '@/lib/result';
import { brandKitSchema, type BrandKit } from '@/schema';

function apiUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) throw new Error('NEXT_PUBLIC_API_URL is not set');
  return url;
}

export async function loadBrand(): Promise<Result<BrandKit>> {
  const res = await fetch(`${apiUrl()}/brand`);
  if (!res.ok) return err(res.status === 404 ? 'not_found' : 'invalid_input', '');
  const parsed = brandKitSchema.safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}

export async function saveBrand(kit: BrandKit): Promise<Result<BrandKit>> {
  // Parsed before the request as well as after it. `displayFont` generated
  // into a Zod enum because `FontId` is a Pydantic `Literal`, so a family
  // string is rejected here without a round trip — which is the same offline
  // guarantee `cta.href`'s pattern gives the editor.
  const valid = brandKitSchema.safeParse(kit);
  if (!valid.success) return err('invalid_input', valid.error.message);

  const res = await fetch(`${apiUrl()}/brand`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(valid.data),
  });
  if (!res.ok) return err('invalid_input', await res.text());
  const parsed = brandKitSchema.safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}
