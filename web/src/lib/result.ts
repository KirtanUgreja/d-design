/**
 * Result: the tagged pair for expected failures.
 *
 * typescript.md: expected failures return a Result; only bugs throw. The
 * compiler forces the caller to handle the failure branch — it cannot be
 * forgotten, and it cannot be a permissive default.
 */

export type Result<T, E = AppError> = { ok: true; value: T } | { ok: false; error: E };

export type AppError = {
  kind: string;
  message: string;
};

export function ok<T>(value: T): Result<T, never> {
  return { ok: true, value };
}

export function err<E>(error: E): Result<never, E> {
  return { ok: false, error };
}
