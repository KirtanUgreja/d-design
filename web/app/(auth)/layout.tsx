import Link from "next/link";

// A cold surface (docs/design/app.md): assembled, not crafted. The wordmark,
// one column, hairlines.
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="mx-auto grid min-h-dvh max-w-6xl grid-rows-[auto_1fr] px-8">
      <header className="py-6">
        <Link href="/" className="font-display text-xl tracking-tight">
          d-design
        </Link>
      </header>
      <section className="grid content-start gap-10 pt-[12vh] pb-16 md:grid-cols-[5fr_7fr]">
        <div className="max-w-sm">{children}</div>
      </section>
    </main>
  );
}
