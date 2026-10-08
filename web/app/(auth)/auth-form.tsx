"use client";
// Sign in and sign up: email and password, nothing else (master plan A2).
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { authClient } from "@/lib/auth-client";
import { meStore } from "@/lib/auth-me";

type Mode = "sign-in" | "sign-up";

const field = (form: FormData, name: string): string => {
  const v = form.get(name);
  return typeof v === "string" ? v : "";
};

export function AuthForm({ mode, next }: { mode: Mode; next: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const signUp = mode === "sign-up";
  const other = signUp ? "/sign-in" : "/sign-up";
  const withNext = (path: string) => (next === "/" ? path : `${path}?next=${encodeURIComponent(next)}`);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const email = field(form, "email").trim();
    const password = field(form, "password");
    setBusy(true);
    setError(null);
    const res = signUp
      ? await authClient.signUp.email({ email, password, name: field(form, "name").trim() || email.split("@")[0] || email })
      : await authClient.signIn.email({ email, password });
    if (res.error) {
      setBusy(false);
      setError(res.error.message ?? (signUp ? "We couldn't create your account." : "That email and password don't match."));
      return;
    }
    meStore.clear();
    router.push(next);
    router.refresh();
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-6">
      <FieldGroup>
        {signUp && (
          <Field>
            <FieldLabel htmlFor="name">Name</FieldLabel>
            <Input id="name" name="name" autoComplete="name" />
          </Field>
        )}
        <Field data-invalid={error ? true : undefined}>
          <FieldLabel htmlFor="email">Email</FieldLabel>
          <Input id="email" name="email" type="email" autoComplete="email" required autoFocus aria-invalid={error ? true : undefined} />
        </Field>
        <Field data-invalid={error ? true : undefined}>
          <FieldLabel htmlFor="password">Password</FieldLabel>
          <Input
            id="password"
            name="password"
            type="password"
            autoComplete={signUp ? "new-password" : "current-password"}
            minLength={signUp ? 10 : undefined}
            required
            aria-invalid={error ? true : undefined}
          />
          {signUp && <FieldDescription>At least 10 characters.</FieldDescription>}
        </Field>
      </FieldGroup>
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <Button type="submit" size="lg" disabled={busy}>
        {signUp ? (busy ? "Creating your account…" : "Create account") : busy ? "Signing in…" : "Sign in"}
      </Button>
      <p className="text-sm text-muted-foreground">
        {signUp ? "Have an account? " : "New here? "}
        <Link href={withNext(other)} className="text-foreground underline underline-offset-4">
          {signUp ? "Sign in" : "Create an account"}
        </Link>
      </p>
    </form>
  );
}
