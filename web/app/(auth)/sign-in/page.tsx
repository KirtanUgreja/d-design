import type { Metadata } from "next";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { AuthForm } from "@/app/(auth)/auth-form";
import { auth } from "@/lib/auth";
import { safeNext } from "@/lib/auth-allow";

export const metadata: Metadata = { title: "Sign in — d-design" };

export default async function SignInPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const next = safeNext((await searchParams).next);
  if (await auth.api.getSession({ headers: await headers() })) redirect(next);
  return (
    <div className="flex flex-col gap-8">
      <h1 className="font-display text-3xl tracking-tight">Sign in</h1>
      <AuthForm mode="sign-in" next={next} />
    </div>
  );
}
