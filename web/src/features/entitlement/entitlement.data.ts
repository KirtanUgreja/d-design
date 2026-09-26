/**
 * The entitlement read — web's server-side path to api's `/entitlements`.
 *
 * api is the authoritative source (web's read is an affordance; api's spend
 * gate is the control). Fail-closed: an unreachable or unhappy api is a
 * refusal, never a default plan — a catch returning a permissive default is a
 * vulnerability, not error handling (AGENTS.md rule 10).
 *
 * `import 'server-only'` keeps the session token off the client bundle.
 */
import 'server-only';

import type { Entitlement, EntitlementRefusal } from './index.js';
import { err, ok, type Result } from '../../lib/result.js';
import { getSessionToken } from '../../lib/session-token.js';

const API_URL = process.env.DDESIGN_API_URL ?? 'http://localhost:8000';

export async function getEntitlement(): Promise<Result<Entitlement, EntitlementRefusal>> {
  const token = await getSessionToken();

  let res: Response;
  try {
    res = await fetch(`${API_URL}/entitlements`, {
      headers: token ? { authorization: `Bearer ${token}` } : {},
      cache: 'no-store',
    });
  } catch {
    return err({ status: 503, message: 'entitlement check unavailable' });
  }
  if (!res.ok) {
    return err({ status: 503, message: `entitlement check failed (${res.status})` });
  }

  const data = (await res.json()) as {
    plan: string;
    used: number;
    limit: number;
    exhausted: boolean;
    kill_switch: boolean;
  };
  return ok({
    plan: data.plan,
    used: data.used,
    limit: data.limit,
    exhausted: data.exhausted,
    killSwitch: data.kill_switch,
  });
}
