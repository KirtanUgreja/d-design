// Defence in depth on `CTA.href`. The schema already enforces the same
// allowlist at generation time (api/schema/scene.py's HREF_PATTERN) — this is
// the render-time copy docs/v1/plan/04-renderer.md asks for, so a value that
// somehow reached the renderer without going through that parse still cannot
// become a `javascript:`/`data:` link. Four lines, per the plan.

const UNSAFE_SCHEME = /^\s*(javascript|data|vbscript):/i;
const PROTOCOL_RELATIVE = /^\s*\/\//;

export function isSafeHref(href: string): boolean {
  return !UNSAFE_SCHEME.test(href) && !PROTOCOL_RELATIVE.test(href);
}
