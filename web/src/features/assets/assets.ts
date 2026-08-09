// The asset client. Upload is a multipart POST and nothing else — no
// client-side validation of the file, deliberately: every one of the six
// controls runs on the server (api/features/assets/upload.py), and a
// client-side check would be a second, weaker copy that an attacker skips by
// not using the client.
//
// What the client *does* own is telling the user what happened, which is why
// the server's message is passed through verbatim rather than replaced with a
// generic one. Six controls means six reasons.

import { err, ok, type Result } from '@/lib/result';
import { assetSchema, type Asset } from '@/schema';
import { z } from 'zod';

function apiUrl(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (!url) throw new Error('NEXT_PUBLIC_API_URL is not set');
  return url;
}

export async function listAssets(): Promise<Result<Asset[]>> {
  const res = await fetch(`${apiUrl()}/assets`);
  if (!res.ok) return err('invalid_input', await res.text());
  const parsed = z.array(assetSchema).safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}

export async function uploadAsset(file: File): Promise<Result<Asset>> {
  const body = new FormData();
  body.append('file', file);

  const res = await fetch(`${apiUrl()}/assets`, { method: 'POST', body });
  if (!res.ok) return err('invalid_input', await detail(res));

  const parsed = assetSchema.safeParse(await res.json());
  if (!parsed.success) return err('invalid_input', parsed.error.message);
  return ok(parsed.data);
}

/** The server's own sentence. Each of the six controls has a different one,
 * and flattening them into "Upload failed" is what the phase doc calls out:
 * a rejected upload is a user holding their own logo, and "Invalid file"
 * answers none of the six questions. */
async function detail(res: Response): Promise<string> {
  const body = await res.text();
  try {
    const parsed: unknown = JSON.parse(body);
    if (parsed !== null && typeof parsed === 'object' && 'detail' in parsed) {
      const { detail: message } = parsed as { detail: unknown };
      if (typeof message === 'string') return message;
    }
  } catch {
    // Not JSON — the raw body is the best available message.
  }
  return body;
}
