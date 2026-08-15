/**
 * Tenant-wrapper test — the fail-closed shape (v3, phase 16).
 *
 * The wrapper is the only place app.user_id is set in TypeScript. The test
 * proves the wrapper runs its work inside a single transaction and the
 * callback receives a transaction with execute (the set_config) available —
 * the structure that scopes set_config to the transaction.
 */
import { describe, expect, it, vi } from 'vitest';

import { asUser } from './tenant.js';

vi.mock('./index.js', () => ({
  db: {
    transaction: vi.fn(async (fn: (tx: { execute: () => Promise<void> }) => Promise<unknown>) =>
      fn({ execute: vi.fn(async () => {}) }),
    ),
  },
}));

describe('tenant wrapper', () => {
  it('runs the callback inside a single transaction with execute available', async () => {
    const dbModule = await import('./index.js');
    const transaction = dbModule.db.transaction as ReturnType<typeof vi.fn>;

    let txSeen: unknown;
    const result = await asUser('user-1', async (tx) => {
      txSeen = tx;
      return 'ok';
    });

    expect(result).toBe('ok');
    expect(transaction).toHaveBeenCalledTimes(1);
    // The callback receives the transaction, whose execute runs the
    // transaction-scoped set_config — the wrapper's contract.
    expect(typeof (txSeen as { execute?: unknown }).execute).toBe('function');
  });
});
