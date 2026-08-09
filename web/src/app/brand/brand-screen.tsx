'use client';

// App-level composition: the brand kit and the asset list on one page
// (docs/v1/plan/10-brand-and-uploads.md).
//
// **It is a page, not a wizard, and that is the sequencing decision the phase
// doc says this phase can quietly break.** The brand kit is asked for
// *second*, after the first artifact exists, framed as "make this yours" — six
// brand fields standing between a new user and their first generation is where
// a first session is lost, and the whole first run has a ninety-second budget.
// So nothing routes here automatically and nothing blocks on it: `/new` works
// with no brand kit at all, and `resolveBrand` already knows what "no brand"
// means.

import { useEffect, useState } from 'react';

import { AssetList, listAssets, uploadAsset } from '@/features/assets';
import { BrandKitForm, loadBrand, saveBrand } from '@/features/brand';
import type { Asset, BrandKit } from '@/schema';

/** What a brand kit looks like before anyone has set one. Not persisted until
 * Save — a row that appears because someone visited a page is a row that lies
 * about intent. */
const BLANK: BrandKit = {
  id: 'new',
  displayFont: 'fraunces',
  textFont: 'inter',
  primary: '#f4b740',
  secondary: '#ffffff',
  neutral: '#888888',
  logoAssetId: null,
};

export function BrandScreen() {
  const [kit, setKit] = useState<BrandKit>(BLANK);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [brandError, setBrandError] = useState<string | null>(null);
  const [assetError, setAssetError] = useState<string | null>(null);

  useEffect(() => {
    void (async () => {
      const existing = await loadBrand();
      // `not_found` is the normal state for a new user, not an error to show.
      if (existing.ok) setKit(existing.value);
      const list = await listAssets();
      if (list.ok) setAssets(list.value);
    })();
  }, []);

  async function persist() {
    setSaving(true);
    const result = await saveBrand(kit);
    setSaving(false);
    if (!result.ok) return setBrandError(result.error.message);
    setBrandError(null);
    setKit(result.value);
  }

  async function upload(file: File) {
    setUploading(true);
    const result = await uploadAsset(file);
    setUploading(false);
    if (!result.ok) {
      // The server's own sentence, passed through. Six controls, six reasons.
      setAssetError(result.error.message);
      return;
    }
    setAssetError(null);
    setAssets((prev) => [result.value, ...prev]);
  }

  return (
    <main className="min-h-screen space-y-10 bg-neutral-950 px-6 py-12 text-neutral-100">
      <BrandKitForm
        kit={kit}
        onChange={setKit}
        onSave={() => void persist()}
        saving={saving}
        error={brandError}
      />
      <AssetList
        assets={assets}
        onUpload={(file) => void upload(file)}
        uploading={uploading}
        error={assetError}
      />
    </main>
  );
}
