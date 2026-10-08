"use client";
// The signed-in user's menu: their avatar, Your decks, Account, Sign out.
// Signed out, it offers Sign in and Create account instead.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { ProfileAvatar, useMe } from "@/components/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { authClient } from "@/lib/auth-client";
import { meStore } from "@/lib/auth-me";

export function UserMenu() {
  const { data, isPending } = authClient.useSession();
  const path = usePathname();
  if (isPending || path.startsWith("/sign-")) return null;
  // ponytail: its own slim row above each page's header; the main session can
  // move it into the page headers when they are unified.
  return (
    <div className="flex items-center justify-end gap-3 px-8 pt-3">
      {data ? (
        <Menu name={data.user.name} email={data.user.email} />
      ) : (
        <>
          <Link href={`/sign-in?next=${encodeURIComponent(path)}`} className="text-sm underline-offset-4 hover:underline">
            Sign in
          </Link>
          <Button asChild size="sm">
            <Link href={`/sign-up?next=${encodeURIComponent(path)}`}>Create account</Link>
          </Button>
        </>
      )}
    </div>
  );
}

function Menu({ name, email }: { name: string; email: string }) {
  const me = useMe();
  const router = useRouter();
  const signOut = async () => {
    await authClient.signOut();
    meStore.clear();
    router.push("/sign-in");
    router.refresh();
  };
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Your account">
          <ProfileAvatar spec={me?.avatar ?? null} name={me?.name ?? name} email={email} size="sm" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-56">
        <DropdownMenuLabel className="flex flex-col gap-0.5">
          <span className="truncate text-foreground">{me?.name || name}</span>
          <span className="truncate font-normal">{email}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem asChild>
            <Link href="/decks">Your decks</Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/account">Account</Link>
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem onSelect={() => void signOut()}>Sign out</DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
