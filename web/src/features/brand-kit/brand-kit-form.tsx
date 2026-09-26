/**
 * The brand-kit form — creating a team and uploading a kit (phase 17).
 *
 * The upload goes through web's own route (`/api/brand-kit/upload`), which
 * forwards the bytes to the worker: it verifies magic bytes, caps the size and
 * re-encodes, and its verdict is fail-closed. Nothing in the browser decides
 * what is a valid image.
 *
 * A team comes first because a kit is team-scoped, and until now teams could
 * only be created by hand in SQL — which is why this form has a team step at
 * all rather than assuming one exists.
 */
'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import type { Team } from './index.js';

export type BrandKitFormProps = {
  teams: Team[];
};

export function BrandKitForm({ teams }: BrandKitFormProps) {
  const router = useRouter();
  const [teamId, setTeamId] = useState(teams[0]?.id ?? '');
  const [teamName, setTeamName] = useState('');
  const [name, setName] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasTeam = teams.length > 0;

  async function handleCreateTeam() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch('/api/teams', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ name: teamName }),
      });
      const data = (await res.json()) as { id?: string; error?: string };
      if (!res.ok) {
        throw new Error(data.error ?? 'could not create the team');
      }
      setTeamId(data.id ?? '');
      setTeamName('');
      router.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (file === null) return;
    setBusy(true);
    setError(null);
    try {
      const body = new FormData();
      body.set('file', file);
      body.set('teamId', teamId);
      body.set('name', name);
      const res = await fetch('/api/brand-kit/upload', { method: 'POST', body });
      const data = (await res.json()) as { kitId?: string; error?: string };
      if (!res.ok) {
        throw new Error(data.error ?? 'upload failed');
      }
      setName('');
      setFile(null);
      router.refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="brand-kits__form">
      {!hasTeam && (
        <div className="brand-kits__team">
          <p>A brand kit belongs to a team, and you have none yet. Create one to start.</p>
          <label>
            Team name
            <input
              value={teamName}
              onChange={(e) => setTeamName(e.target.value)}
              placeholder="My team"
            />
          </label>
          <button onClick={handleCreateTeam} disabled={busy || teamName.trim() === ''}>
            Create team
          </button>
        </div>
      )}

      {hasTeam && (
        <form onSubmit={handleUpload}>
          <label>
            Team
            <select value={teamId} onChange={(e) => setTeamId(e.target.value)}>
              {teams.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Kit name
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </label>
          <label>
            Logo
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp,image/svg+xml"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              required
            />
          </label>
          <button type="submit" disabled={busy || file === null || name.trim() === ''}>
            {busy ? 'Uploading…' : 'Upload kit'}
          </button>
        </form>
      )}

      {error && <div className="brand-kits__error">{error}</div>}
    </div>
  );
}
