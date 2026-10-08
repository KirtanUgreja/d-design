import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";

import { DecksList } from "@/app/decks/decks-list";
import { Button } from "@/components/ui/button";
import { auth } from "@/lib/auth";

export const metadata: Metadata = { title: "Your decks — d-design" };

export default async function DecksPage() {
  // The real check; proxy.ts only looked for a cookie.
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) redirect("/sign-in?next=/decks");
  return (
    <main className="mx-auto max-w-[1440px] px-4 pb-20 sm:px-8">
      <div className="flex flex-wrap items-end justify-between gap-4 py-10">
        <h1 className="font-display text-[40px] leading-none tracking-[-0.02em]">Your decks</h1>
        <Button asChild>
          <Link href="/">New deck</Link>
        </Button>
      </div>
      <DecksList />
    </main>
  );
}
