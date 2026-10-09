"use client";
// Forgot password and choose a new one (owner, 2026-10-10). The request
// always answers the same way, so it never tells whether an address has an
// account; the link in the email works once, for 30 minutes.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { authClient } from "@/lib/auth-client";

export function ForgotForm() {
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const email = new FormData(e.currentTarget).get("email");
    if (typeof email !== "string" || !email.trim()) return;
    setBusy(true);
    setError(null);
    const res = await authClient.requestPasswordReset({ email: email.trim(), redirectTo: "/reset-password" });
    setBusy(false);
    // Rate limits and outages are worth saying; "no such account" never is.
    if (res.error && res.error.status !== 404) return setError(res.error.message ?? "We couldn't send it. Try again in a minute.");
    setSent(true);
  }

  if (sent) {
    return (
      <div className="flex flex-col gap-4">
        <Alert>
          <AlertDescription>
            If that address has an account, a link to choose a new password is on its way. It works once, for 30 minutes.
          </AlertDescription>
        </Alert>
        <Link href="/sign-in" className="text-sm underline underline-offset-4">
          Back to sign in
        </Link>
      </div>
    );
  }
  return (
    <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-6">
      <FieldGroup>
        <Field>
          <FieldLabel htmlFor="email">Email</FieldLabel>
          <Input className="h-11 bg-paper text-[15px]" id="email" name="email" type="email" autoComplete="email" required autoFocus />
        </Field>
      </FieldGroup>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <Button type="submit" size="lg" className="h-11" disabled={busy}>
        {busy ? "Sending…" : "Send the link"}
      </Button>
      <Link href="/sign-in" className="text-sm text-muted-foreground underline underline-offset-4">
        Back to sign in
      </Link>
    </form>
  );
}

export function ResetForm({ token }: { token: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const password = form.get("password");
    const again = form.get("again");
    if (typeof password !== "string" || password !== again) return setError("The two passwords don't match.");
    setBusy(true);
    setError(null);
    const res = await authClient.resetPassword({ newPassword: password, token });
    setBusy(false);
    if (res.error) return setError("That link has expired or was already used. Ask for a new one.");
    router.push("/sign-in?reset=1");
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-6">
      <FieldGroup>
        <Field>
          <FieldLabel htmlFor="password">New password</FieldLabel>
          <Input className="h-11 bg-paper text-[15px]" id="password" name="password" type="password" autoComplete="new-password" minLength={10} required autoFocus />
          <FieldDescription>At least 10 characters.</FieldDescription>
        </Field>
        <Field>
          <FieldLabel htmlFor="again">The same again</FieldLabel>
          <Input className="h-11 bg-paper text-[15px]" id="again" name="again" type="password" autoComplete="new-password" minLength={10} required />
        </Field>
      </FieldGroup>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>
            {error}{" "}
            <Link href="/forgot-password" className="underline underline-offset-4">
              New link
            </Link>
          </AlertDescription>
        </Alert>
      )}
      <Button type="submit" size="lg" className="h-11" disabled={busy}>
        {busy ? "Saving…" : "Save the new password"}
      </Button>
    </form>
  );
}
