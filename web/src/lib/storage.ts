import 'server-only';

// The publish artifact store. v1's answer to "storage.ts" for this concern
// is local disk, not the S3/MinIO abstraction api/lib/storage.py already
// built for uploads (docs/v1/spec.md: "Publishing in v1 is a web route
// writing to local disk"). Same shape either way — read/write by id, a
// Result on read — so the v3 move to S3 + CloudFront
// (docs/v1/plan/05-publish-present-embed.md -> Skipped) is a destination
// change behind this file, not a rewrite of anything that calls it.

import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

import { err, ok, type Result } from '@/lib/result';

const ROOT = join(process.cwd(), '.data', 'published');

// Experience ids are UUIDs, always server-generated (api/db/models.py). This
// is the path-traversal guard uploads.md asks for, applied to the one other
// place a caller-supplied string reaches a filesystem path.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function pathFor(id: string): Result<string> {
  if (!UUID_RE.test(id)) return err('invalid_input', `not a valid experience id: ${id}`);
  return ok(join(ROOT, `${id}.json`));
}

export async function writeArtifact(
  id: string,
  artifact: unknown,
): Promise<Result<void>> {
  const path = pathFor(id);
  if (!path.ok) return path;
  await mkdir(ROOT, { recursive: true });
  await writeFile(path.value, JSON.stringify(artifact), 'utf8');
  return ok(undefined);
}

export async function readArtifact(id: string): Promise<Result<unknown>> {
  const path = pathFor(id);
  if (!path.ok) return path;
  try {
    return ok(JSON.parse(await readFile(path.value, 'utf8')) as unknown);
  } catch (e) {
    if (e instanceof Error && 'code' in e && e.code === 'ENOENT') {
      return err('not_found', id);
    }
    throw e;
  }
}

export async function deleteArtifact(id: string): Promise<Result<void>> {
  const path = pathFor(id);
  if (!path.ok) return path;
  await rm(path.value, { force: true });
  return ok(undefined);
}
