import Link from "next/link";

export default function NotFound() {
  return (
    <main className="mx-auto grid min-h-dvh max-w-xl content-center gap-4 px-8">
      <h1 className="font-display text-3xl">There’s no deck here.</h1>
      <Link href="/" className="underline">
        Start a new one
      </Link>
    </main>
  );
}
