"use client";
// The account page: who you are and what you've made, name, password, the
// avatar and its picker, a small game, sign out, delete (owner, 2026-10-10:
// "too small and boring"). Hairlines only, like the rest of the chrome.
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { ColourGame } from "@/components/colour-game";
import { loadDecks } from "@/lib/decks";

import { ProfileAvatar, useAvatarUri, useMe } from "@/components/avatar";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldGroup, FieldLabel, FieldLegend, FieldSet } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { authClient } from "@/lib/auth-client";
import {
  AVATAR_BACKGROUNDS,
  AVATAR_STYLES,
  meApi,
  meStore,
  newSeed,
  type AvatarSpec,
  type AvatarStyle,
} from "@/lib/auth-me";

export function AccountView({ user }: { user: { name: string; email: string } }) {
  const me = useMe();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState("");

  async function saveAvatar(next: AvatarSpec) {
    if (!me) return;
    const before = me;
    meStore.set({ ...me, avatar: next }); // optimistic: the face changes at once
    setStatus("Saving…");
    const res = await meApi.save({ avatar: next });
    if (!res.ok) {
      meStore.set(before);
      setStatus("");
      setError(res.error);
      return;
    }
    meStore.set(res.value);
    setError(null);
    setStatus("Saved");
  }

  async function saveName(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const raw = new FormData(e.currentTarget).get("name");
    const name = typeof raw === "string" ? raw.trim() : "";
    if (!name) return setError("Your name can't be empty.");
    setStatus("Saving…");
    // Both copies: Better Auth's (it goes into the API's token) and the API's.
    const a = await authClient.updateUser({ name });
    const b = await meApi.save({ name });
    if (a.error || !b.ok) {
      setStatus("");
      return setError(a.error?.message ?? (b.ok ? "We couldn't save your name." : b.error));
    }
    meStore.set(b.value);
    setError(null);
    setStatus("Saved");
    router.refresh();
  }

  async function signOut() {
    await authClient.signOut();
    meStore.clear();
    router.push("/sign-in");
    router.refresh();
  }

  const avatar = me?.avatar ?? null;
  const name = me?.name || user.name;

  return (
    <div className="flex flex-col gap-10 pt-8 pb-6">
      <header className="flex flex-col gap-6 border-b border-rule pb-8 sm:flex-row sm:items-center sm:gap-8">
        {me ? (
          <ProfileAvatar spec={avatar} name={name} email={user.email} size="lg" className="size-24 sm:size-28" />
        ) : (
          <Skeleton className="size-24 rounded-full sm:size-28" />
        )}
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h1 id="profile" className="truncate font-display text-[34px] leading-tight tracking-[-0.015em] sm:text-[44px]">
            {name}
          </h1>
          <p className="truncate text-[15px] text-ink-2">{user.email}</p>
        </div>
        <Made />
      </header>

      <div className="grid gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)] lg:gap-14">
        <div className="flex flex-col gap-10">
          <section aria-labelledby="details" className="flex flex-col gap-5">
            <h2 id="details" className="font-display text-2xl tracking-tight">
              Your details
            </h2>
            <form onSubmit={(e) => void saveName(e)} className="flex flex-col gap-4">
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="name">Name</FieldLabel>
                  <Input id="name" name="name" defaultValue={name} key={name} autoComplete="name" className="h-11 text-[15px]" />
                </Field>
                <Field>
                  <FieldLabel htmlFor="email">Email</FieldLabel>
                  <Input id="email" value={user.email} readOnly disabled className="h-11 text-[15px]" />
                  <FieldDescription>Email can&apos;t be changed in this preview.</FieldDescription>
                </Field>
              </FieldGroup>
              <div className="flex items-center gap-4">
                <Button type="submit" variant="outline">
                  Save name
                </Button>
                <p role="status" aria-live="polite" className="text-sm text-muted-foreground">
                  {status}
                </p>
              </div>
            </form>
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
          </section>
          <Separator />
          <ChangePassword />
          <Separator />
          <section aria-labelledby="leave" className="flex flex-col gap-4">
            <h2 id="leave" className="font-display text-2xl tracking-tight">
              Sign out or leave
            </h2>
            <div className="flex flex-wrap gap-3">
              <Button variant="outline" onClick={() => void signOut()}>
                Sign out
              </Button>
              <DeleteAccount />
            </div>
          </section>
        </div>

        <div className="flex flex-col gap-10">
          <section aria-labelledby="avatar-heading" className="flex flex-col gap-6 border border-rule p-5 sm:p-6">
            <div className="flex items-baseline justify-between gap-4">
              <h2 id="avatar-heading" className="font-display text-2xl tracking-tight">
                Avatar
              </h2>
              <Button variant="outline" disabled={!avatar} onClick={() => avatar && void saveAvatar({ ...avatar, seed: newSeed() })}>
                Shuffle
              </Button>
            </div>
            {avatar ? (
              <>
                <FieldSet>
                  <FieldLegend variant="label">Style</FieldLegend>
                  <ToggleGroup
                    type="single"
                    variant="outline"
                    spacing={2}
                    value={avatar.style}
                    onValueChange={(v) => {
                      const style = AVATAR_STYLES.find((s) => s.id === v)?.id;
                      if (style) void saveAvatar({ ...avatar, style });
                    }}
                    className="grid grid-cols-3"
                  >
                    {AVATAR_STYLES.map((s) => (
                      <ToggleGroupItem key={s.id} value={s.id} className="h-auto flex-col gap-2 py-3">
                        <StylePreview spec={{ ...avatar, style: s.id }} />
                        {s.label}
                      </ToggleGroupItem>
                    ))}
                  </ToggleGroup>
                </FieldSet>
                <FieldSet>
                  <FieldLegend variant="label">Background</FieldLegend>
                  <ToggleGroup
                    type="single"
                    variant="outline"
                    spacing={2}
                    value={avatar.options.backgroundColor}
                    onValueChange={(v) => {
                      const bg = AVATAR_BACKGROUNDS.find((b) => b.hex === v)?.hex;
                      if (bg) void saveAvatar({ ...avatar, options: { backgroundColor: bg } });
                    }}
                    className="flex-wrap"
                  >
                    {AVATAR_BACKGROUNDS.map((b) => (
                      <ToggleGroupItem key={b.hex} value={b.hex} aria-label={b.label} className="gap-2">
                        <span aria-hidden="true" className="size-4 rounded-full border border-rule" style={{ backgroundColor: b.hex }} />
                        {b.label}
                      </ToggleGroupItem>
                    ))}
                  </ToggleGroup>
                </FieldSet>
              </>
            ) : (
              <Skeleton className="h-48 w-full" />
            )}
            <p className="text-xs text-muted-foreground">
              Avatars are drawn on your device by DiceBear (MIT). Styles:{" "}
              {AVATAR_STYLES.map((s) => `${s.label} by ${s.artist}`).join(", ")} — all {AVATAR_STYLES[0].license}.
            </p>
          </section>
          <ColourGame />
        </div>
      </div>
    </div>
  );
}

// What you've made here, from your deck list.
function Made() {
  const [made, setMade] = useState<{ decks: number; slides: number } | null>(null);
  useEffect(() => {
    let live = true;
    void loadDecks().then((r) => {
      if (live && r?.ok) {
        const built = r.value.filter((d) => d.status === "ready");
        setMade({ decks: built.length, slides: built.reduce((n, d) => n + d.slides, 0) });
      }
    });
    return () => {
      live = false;
    };
  }, []);
  if (!made) return null;
  return (
    <Link href="/decks" className="group flex gap-8 sm:border-l sm:border-rule sm:pl-8">
      <span className="flex flex-col">
        <span className="font-display text-[34px] leading-none tabular-nums">{made.decks}</span>
        <span className="mt-1 placard group-hover:text-ink">Decks built</span>
      </span>
      <span className="flex flex-col">
        <span className="font-display text-[34px] leading-none tabular-nums">{made.slides}</span>
        <span className="mt-1 placard group-hover:text-ink">Slides designed</span>
      </span>
    </Link>
  );
}

function ChangePassword() {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const data = new FormData(form);
    const current = data.get("current");
    const next = data.get("next");
    if (typeof current !== "string" || typeof next !== "string") return;
    setBusy(true);
    setError(null);
    setDone(false);
    const res = await authClient.changePassword({ currentPassword: current, newPassword: next, revokeOtherSessions: true });
    setBusy(false);
    if (res.error) return setError(res.error.message ?? "We couldn't change your password.");
    form.reset();
    setDone(true);
  }

  return (
    <section aria-labelledby="password" className="flex flex-col gap-5">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id="password" className="font-display text-2xl tracking-tight">
          Password
        </h2>
        <Link href="/forgot-password" className="text-[13px] text-ink-2 underline-offset-4 hover:text-ink hover:underline">
          Forgot it?
        </Link>
      </div>
      <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-4">
        <FieldGroup>
          <Field data-invalid={error ? true : undefined}>
            <FieldLabel htmlFor="current">Current password</FieldLabel>
            <Input id="current" name="current" type="password" autoComplete="current-password" required className="h-11 text-[15px]" aria-invalid={error ? true : undefined} />
          </Field>
          <Field>
            <FieldLabel htmlFor="next">New password</FieldLabel>
            <Input id="next" name="next" type="password" autoComplete="new-password" minLength={10} required className="h-11 text-[15px]" />
            <FieldDescription>At least 10 characters. Your other devices are signed out.</FieldDescription>
          </Field>
        </FieldGroup>
        <div className="flex items-center gap-4">
          <Button type="submit" variant="outline" disabled={busy}>
            {busy ? "Changing…" : "Change password"}
          </Button>
          <p role="status" aria-live="polite" className={error ? "text-sm text-flag" : "text-sm text-muted-foreground"}>
            {error ?? (done ? "Changed." : "")}
          </p>
        </div>
      </form>
    </section>
  );
}

function StylePreview({ spec }: { spec: AvatarSpec & { style: AvatarStyle } }) {
  const uri = useAvatarUri(spec);
  // eslint-disable-next-line @next/next/no-img-element -- a local data: URI, not a remote image
  return uri ? <img src={uri} alt="" className="size-12 rounded-full" /> : <Skeleton className="size-12 rounded-full" />;
}

function DeleteAccount() {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function remove(e: React.MouseEvent) {
    e.preventDefault(); // keep the dialog open until it has worked
    setBusy(true);
    const res = await authClient.deleteUser({ password });
    setBusy(false);
    if (res.error) return setError(res.error.message ?? "We couldn't delete your account.");
    meStore.clear();
    router.push("/sign-up");
    router.refresh();
  }

  return (
    <AlertDialog onOpenChange={() => (setPassword(""), setError(null))}>
      <AlertDialogTrigger asChild>
        <Button variant="destructive">Delete account</Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete your account?</AlertDialogTitle>
          <AlertDialogDescription>
            Your decks and their files are deleted with it. This can&apos;t be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <Field data-invalid={error ? true : undefined}>
          <FieldLabel htmlFor="delete-password">Your password</FieldLabel>
          <Input
            id="delete-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={error ? true : undefined}
          />
          {error && <FieldDescription>{error}</FieldDescription>}
        </Field>
        <AlertDialogFooter>
          <AlertDialogCancel>Keep my account</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={!password || busy} onClick={(e) => void remove(e)}>
            {busy ? "Deleting…" : "Delete account"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
