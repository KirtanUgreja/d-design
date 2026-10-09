import type { Metadata } from "next";
import Link from "next/link";

import { ForgotForm } from "@/app/(auth)/reset-forms";
import { canResetPassword } from "@/lib/auth";

export const metadata: Metadata = { title: "Forgot password — d-design" };

export default function ForgotPasswordPage() {
  const ready = canResetPassword();
  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <h1 className="font-display text-[40px] leading-none tracking-[-0.02em]">Forgot password</h1>
        <p className="text-sm text-muted-foreground">
          {ready
            ? "Give your email and we'll send a link to choose a new password."
            : "Password reset by email isn't switched on for this preview yet. Ask the owner to reset it for you."}
        </p>
      </div>
      {ready ? (
        <ForgotForm />
      ) : (
        <Link href="/sign-in" className="text-sm underline underline-offset-4">
          Back to sign in
        </Link>
      )}
    </div>
  );
}
