"use client";
// The account page: name, email, the avatar and its picker, sign out, delete.
// A cold surface (docs/design/app.md): assembled from the kit, hairlines only.
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

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
    <div className="grid gap-12 pt-10 md:grid-cols-[5fr_7fr]">
      <section aria-labelledby="profile" className="flex flex-col gap-6">
        <div className="flex items-center gap-4">
          {me ? (
            <ProfileAvatar spec={avatar} name={name} email={user.email} size="lg" className="size-20" />
          ) : (
            <Skeleton className="size-20 rounded-full" />
          )}
          <div className="flex min-w-0 flex-col">
            <h1 id="profile" className="truncate font-display text-3xl tracking-tight">
              {name}
            </h1>
            <p className="truncate text-sm text-muted-foreground">{user.email}</p>
          </div>
        </div>
        <form onSubmit={(e) => void saveName(e)} className="flex flex-col gap-4">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="name">Name</FieldLabel>
              <Input id="name" name="name" defaultValue={name} key={name} autoComplete="name" />
            </Field>
            <Field>
              <FieldLabel htmlFor="email">Email</FieldLabel>
              <Input id="email" value={user.email} readOnly disabled />
              <FieldDescription>Email can&apos;t be changed in this preview.</FieldDescription>
            </Field>
          </FieldGroup>
          <div>
            <Button type="submit" variant="outline">
              Save name
            </Button>
          </div>
        </form>
        <p role="status" aria-live="polite" className="min-h-5 text-sm text-muted-foreground">
          {status}
        </p>
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <Separator />
        <div className="flex flex-wrap gap-3">
          <Button variant="outline" onClick={() => void signOut()}>
            Sign out
          </Button>
          <DeleteAccount />
        </div>
      </section>

      <section aria-labelledby="avatar-heading" className="flex flex-col gap-6">
        <div className="flex items-baseline justify-between gap-4">
          <h2 id="avatar-heading" className="font-display text-2xl tracking-tight">
            Avatar
          </h2>
          <Button
            variant="outline"
            disabled={!avatar}
            onClick={() => avatar && void saveAvatar({ ...avatar, seed: newSeed() })}
          >
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
    </div>
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
