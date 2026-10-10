import type { Metadata } from "next";
import { headers } from "next/headers";
import { redirect } from "next/navigation";

import { AuthForm } from "@/app/(auth)/auth-form";
import { auth } from "@/lib/auth";
import { safeNext } from "@/lib/auth-allow";

export const metadata: Metadata = { title: "Create an account — d-design" };

export default async function SignUpPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const next = safeNext((await searchParams).next);
  if (await auth.api.getSession({ headers: await headers() })) redirect(next);
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-[40px] leading-none tracking-[-0.02em]">Create an account</h1>
        <p className="text-sm text-muted-foreground">This preview is open to invited emails only.</p>
      </div>
      <AuthForm mode="sign-up" next={next} />
    </div>
  );
}
