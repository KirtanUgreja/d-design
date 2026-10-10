// Who may sign up, and where a signed-in user may be sent back to. Pure, so
// both the auth server and the proxy use the same rules.

/** `ALLOWED_EMAILS` is comma-separated, trimmed, case-insensitive. Empty means nobody (fail closed). */
export function isAllowedEmail(email: unknown, allowed: string | undefined): boolean {
  if (typeof email !== "string") return false;
  const want = email.trim().toLowerCase();
  if (!want) return false;
  const list = (allowed ?? "")
    .split(",")
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean);
  return list.includes(want);
}

/** A return path from the query string, kept on this site: "/x" yes, "//evil" and "https://…" no. */
export function safeNext(raw: unknown): string {
  if (typeof raw !== "string" || !raw.startsWith("/") || raw.startsWith("//") || raw.startsWith("/\\")) return "/";
  return raw;
}
