/**
 * The storage abstraction — the documented `storage.ts` (decisions.md: "local
 * disk → S3 (MinIO locally)").
 *
 * Uploaded files land under server-generated UUID keys (never a user
 * filename — path traversal is structurally impossible). The interface is
 * what phase 18 (hosting) swaps for S3/MinIO.
 *
 * ponytail: local disk only for now. S3 lands with hosting; a service that
 * exists but is unused is worse than one that lands with its first consumer.
 */
import 'server-only';

import { randomUUID } from 'node:crypto';
import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';

/** A stored object: its server key and the bytes. */
export interface StoredObject {
  key: string;
  bytes: Buffer;
  contentType: string;
}

export interface Storage {
  /** Write bytes under a new server-generated key. Returns the key. */
  put(bytes: Buffer, contentType: string): Promise<string>;
  /** Read an object by its key. Throws if missing. */
  get(key: string): Promise<StoredObject>;
  /** Remove an object by its key. */
  delete(key: string): Promise<void>;
}

const ROOT = process.env.ASSETS_DIR ?? path.join(process.cwd(), 'assets');

/** Local-disk storage: UUID keys under ASSETS_DIR, content-type map for
 * serving. */
class DiskStorage implements Storage {
  async put(bytes: Buffer, contentType: string): Promise<string> {
    const key = `${randomUUID()}.bin`;
    await mkdir(ROOT, { recursive: true });
    await writeFile(path.join(ROOT, key), bytes);
    await writeFile(path.join(ROOT, `${key}.type`), contentType);
    return key;
  }

  async get(key: string): Promise<StoredObject> {
    // The key is server-generated (a UUID); this join is safe, but the check
    // is the honest guard against any caller passing a path-shaped key.
    if (key.includes('/') || key.includes('..')) {
      throw new Error(`invalid storage key: ${key}`);
    }
    const bytes = await readFile(path.join(ROOT, key));
    const contentType = await readFile(path.join(ROOT, `${key}.type`), 'utf8');
    return { key, bytes, contentType };
  }

  async delete(key: string): Promise<void> {
    await rm(path.join(ROOT, key), { force: true });
    await rm(path.join(ROOT, `${key}.type`), { force: true });
  }
}

export const storage: Storage = new DiskStorage();
