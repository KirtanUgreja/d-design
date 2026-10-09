import type { Metadata } from "next";
import Link from "next/link";

import { ResetForm } from "@/app/(auth)/reset-forms";

export const metadata: Metadata = { title: "New password — d-design" };

export default async function ResetPasswordPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const params = await searchParams;
  const token = typeof params.token === "string" ? params.token : "";
  const bad = !token || params.error !== undefined;
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-[40px] leading-none tracking-[-0.02em]">Choose a new password</h1>
        <p className="text-sm text-muted-foreground">
          {bad ? "That link has expired or was already used." : "Every other device will be signed out."}
        </p>
      </div>
      {bad ? (
        <Link href="/forgot-password" className="text-sm underline underline-offset-4">
          Send a new link
        </Link>
      ) : (
        <ResetForm token={token} />
      )}
    </div>
  );
}
