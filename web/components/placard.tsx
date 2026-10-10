// The placard: the small label under a slide or a deck, like the card beside a
// print on a gallery wall (docs/design/brand.md). What it is, and where it
// stands; the number in the display face when order means something.
import { cn } from "@/lib/utils";

export function Placard({
  lead,
  label,
  aside,
  flag = false,
  className,
}: {
  lead?: string;
  label: string;
  aside?: string;
  flag?: boolean;
  className?: string;
}) {
  return (
    <p className={cn("mt-2.5 flex items-baseline gap-2 border-t border-rule pt-2 placard", className)}>
      {lead && <span className="font-display text-[13px] tracking-normal text-ink normal-case">{lead}</span>}
      <span className="truncate">{label}</span>
      {aside && <span className={cn("ml-auto shrink-0", flag && "text-flag")}>{aside}</span>}
    </p>
  );
}
