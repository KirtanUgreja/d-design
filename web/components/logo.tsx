// The wordmark: "d-design" in the display face, its hyphen a small slide — a
// 16:9 frame with a headline bar — so the name itself says what it makes. The
// same slide is the tab icon (app/icon.svg).
import { cn } from "@/lib/utils";

export function SlideMark({ className, bar = "currentColor" }: { className?: string; bar?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 18 11" className={className}>
      <rect x="0.8" y="0.8" width="16.4" height="9.4" rx="1.4" fill="none" stroke="currentColor" strokeWidth="1.6" />
      <rect x="3.6" y="3.5" width="7.4" height="1.6" rx="0.4" fill={bar} />
      <rect x="3.6" y="6.3" width="4.4" height="1.1" rx="0.4" fill="currentColor" opacity="0.5" />
    </svg>
  );
}

export function Logo({ className, bar }: { className?: string; bar?: string }) {
  return (
    <span role="img" aria-label="d-design" className={cn("inline-flex items-center font-display font-medium leading-none tracking-[-0.02em]", className)}>
      <span aria-hidden="true">d</span>
      <SlideMark bar={bar} className="mx-[0.15em] mt-[0.12em] h-[0.44em] w-[0.72em] shrink-0" />
      <span aria-hidden="true">design</span>
    </span>
  );
}
