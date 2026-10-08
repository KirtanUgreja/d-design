// A small drawn chevron: the ▾ glyph renders as a dot in our text face.
export function Chevron({ className = "" }: { className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 10 6" width="10" height="6" className={className}>
      <path d="M1 1l4 4 4-4" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
