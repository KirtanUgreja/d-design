// A slide as the QA screenshot the engine took: what was measured is what is shown.
/* eslint-disable @next/next/no-img-element -- fixture screenshots, sized by us */
export function SlideThumb({
  src,
  alt,
  className = "",
}: {
  src: string;
  alt: string;
  className?: string;
}) {
  return (
    <img
      src={src}
      alt={alt}
      width={1920}
      height={1080}
      className={`block aspect-video h-auto w-full border border-rule bg-paper-2 ${className}`}
      draggable={false}
    />
  );
}
