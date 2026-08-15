/**
 * The storage abstraction — the documented `storage.ts` (decisions.md: "local
 * disk → S3 (MinIO locally)").
 *
 * Phase 18: the ponytail resolves — storage now talks the S3 API locally
 * (MinIO in docker-compose, same protocol) and in production (real S3). One
 * code path; the endpoint is environment config. The AWS SDK picks up real
 * credentials from the environment in prod; in dev they come from the
 * docker-compose MinIO credentials.
 *
 * Uploaded files land under server-generated UUID keys (never a user
 * filename — path traversal is structurally impossible). Server-set
 * Content-Type on put; the key is the only identity.
 */
import 'server-only';

import { randomUUID } from 'node:crypto';

import {
  DeleteObjectCommand,
  GetObjectCommand,
  PutObjectCommand,
  S3Client,
} from '@aws-sdk/client-s3';

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

const BUCKET = process.env.S3_BUCKET ?? 'ddesign-assets';

/** The S3 endpoint. Dev: MinIO (docker-compose). Prod: unset → the AWS SDK
 * resolves the real regional endpoint. This is the one infra knob. */
const ENDPOINT = process.env.S3_ENDPOINT;

// Fail-closed: if an endpoint is configured but no credentials are present,
// let the SDK throw on first use rather than falling back to a permissive
// anonymous path (patterns.md rule 5). In prod the SDK resolves credentials
// from the environment/instance role; in dev the compose MinIO creds are set.
const client = new S3Client({
  ...(ENDPOINT ? { endpoint: ENDPOINT, forcePathStyle: true } : {}),
  region: process.env.S3_REGION ?? 'us-east-1',
});

/** S3 storage (MinIO locally, real S3 in prod): UUID keys, server-set
 * Content-Type. */
class S3Storage implements Storage {
  async put(bytes: Buffer, contentType: string): Promise<string> {
    const key = `${randomUUID()}.bin`;
    await client.send(
      new PutObjectCommand({
        Bucket: BUCKET,
        Key: key,
        Body: bytes,
        ContentType: contentType,
        // Content-hashed objects are immutable; long-lived cache.
        CacheControl: 'public, max-age=31536000, immutable',
      }),
    );
    return key;
  }

  async get(key: string): Promise<StoredObject> {
    // The key is server-generated (a UUID); this guard is the honest check
    // against any caller passing a path-shaped key.
    if (key.includes('/') || key.includes('..')) {
      throw new Error(`invalid storage key: ${key}`);
    }
    const res = await client.send(new GetObjectCommand({ Bucket: BUCKET, Key: key }));
    const bytes = (await res.Body?.transformToByteArray()) ?? new Uint8Array();
    return {
      key,
      bytes: Buffer.from(bytes),
      contentType: res.ContentType ?? 'application/octet-stream',
    };
  }

  async delete(key: string): Promise<void> {
    await client.send(new DeleteObjectCommand({ Bucket: BUCKET, Key: key }));
  }
}

export const storage: Storage = new S3Storage();
