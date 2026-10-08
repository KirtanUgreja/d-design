"use client";
// The one bar every page shares: the wordmark, the two places a signed-in
// person goes (a new deck, their decks) and their account. Signed out it
// offers Sign in and Create account; on the sign-in pages only the wordmark.
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
import { cn } from "@/lib/utils";

export function AppBar() {
  const { data, isPending } = authClient.useSession();
  const path = usePathname();
  const authPage = path.startsWith("/sign-");
  const here = (href: string) => (href === "/" ? path === "/" : path.startsWith(href));

  return (
    <header className="sticky top-0 z-30 border-b border-rule bg-paper">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-6 px-4 sm:px-8">
        <Link href="/" className="font-display text-[22px] leading-none tracking-[-0.015em]">
          d-design
        </Link>
        {data && !authPage && (
          <nav aria-label="Main" className="flex items-center gap-5 text-sm">
            {[
              { href: "/", label: "New deck" },
              { href: "/decks", label: "Your decks" },
            ].map((l) => (
              <Link
                key={l.href}
                href={l.href}
                aria-current={here(l.href) ? "page" : undefined}
                className={cn(
                  "py-1 text-ink-2 underline-offset-[6px] transition-colors hover:text-ink",
                  here(l.href) && "text-ink underline decoration-1",
                )}
              >
                {l.label}
              </Link>
            ))}
          </nav>
        )}
        <div className="ml-auto flex items-center gap-4">
          {isPending || authPage ? null : data ? (
            <Menu name={data.user.name} email={data.user.email} />
          ) : (
            <>
              <Link
                href={`/sign-in?next=${encodeURIComponent(path)}`}
                className="text-sm text-ink-2 underline-offset-4 hover:text-ink hover:underline"
              >
                Sign in
              </Link>
              <Button asChild size="sm">
                <Link href={`/sign-up?next=${encodeURIComponent(path)}`}>Create account</Link>
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
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
        <Button variant="ghost" size="icon" aria-label="Your account" className="rounded-full">
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
