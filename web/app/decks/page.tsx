import type { Metadata } from "next";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { DecksList } from "@/app/decks/decks-list";
import { PageHead } from "@/app/decks/page-head";
import { auth } from "@/lib/auth";

export const metadata: Metadata = { title: "Your decks — d-design" };

export default async function DecksPage() {
  // The real check; proxy.ts only looked for a cookie.
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) redirect("/sign-in?next=/decks");
  return (
    <main className="mx-auto max-w-6xl px-8 pb-16">
      <PageHead current="decks" />
      <DecksList user={{ name: session.user.name, email: session.user.email }} />
    </main>
  );
}
