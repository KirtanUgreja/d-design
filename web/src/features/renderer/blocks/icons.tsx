// The `checks` list style needs an icon. Drawn as inline SVG from tokens
// rather than an icon dependency (docs/v1/plan/04-renderer.md).

export function CheckIcon({ color }: { color: string }) {
  return (
    <svg
      viewBox="0 0 16 16"
      width="1em"
      height="1em"
      aria-hidden="true"
      style={{ flexShrink: 0 }}
    >
      <path
        d="M3 8.5 6.5 12 13 4.5"
        fill="none"
        stroke={color}
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
