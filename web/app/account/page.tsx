import type { Metadata } from "next";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { AccountView } from "@/app/account/account-view";
import { auth } from "@/lib/auth";

export const metadata: Metadata = { title: "Account — d-design" };

export default async function AccountPage() {
  // The real check; proxy.ts only looked for a cookie.
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) redirect("/sign-in?next=/account");
  return (
    <main className="mx-auto max-w-[1440px] px-4 pb-20 sm:px-8">
      <AccountView user={{ name: session.user.name, email: session.user.email }} />
    </main>
  );
}
