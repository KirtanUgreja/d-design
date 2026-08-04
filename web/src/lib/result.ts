// The one error type. Expected failures return a Result; bugs throw.
// docs/coderules/typescript.md -> "Errors"
//
// web had no data layer and no failure to model until now — phase 03's brand
// resolver is the trigger phase 00 named: "if it ends up used by one feature,
// move it into that feature" doesn't apply here because this is exactly the
// kind of thing every feature needs and none should own.

export type AppErrorCode =
  | 'invalid_input'
  | 'unauthorized'
  | 'not_found'
  | 'quota_exceeded'
  | 'upstream_unavailable';

export interface AppError {
  code: AppErrorCode;
  message: string;
}

export type Result<T, E = AppError> = { ok: true; value: T } | { ok: false; error: E };

export function ok<T>(value: T): Result<T, never> {
  return { ok: true, value };
}

export function err(code: AppErrorCode, message = ''): Result<never, AppError> {
  return { ok: false, error: { code, message } };
}
