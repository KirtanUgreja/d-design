"use client";
// The one bar every page shares: the wordmark, the two places a signed-in
// person goes (a new deck, their decks) and their account. Signed out it
// offers Sign in and Create account; on the sign-in pages only the wordmark.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { ProfileAvatar, useMe } from "@/components/avatar";
import { Chevron } from "@/components/chevron";
import { Logo } from "@/components/logo";
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
  const authPage = ["/sign-", "/forgot-password", "/reset-password"].some((p) => path.startsWith(p));
  const here = (href: string) => (href === "/" ? path === "/" : path.startsWith(href));
  // The sign-in pages carry the wordmark in their own stage.
  if (authPage) return null;

  return (
    <header className="sticky top-0 z-30 border-b border-rule bg-paper">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center gap-6 px-4 sm:px-8">
        <Link href="/" aria-label="d-design, home" className="text-[24px]">
          <Logo bar="var(--color-accent)" />
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
        <button
          type="button"
          aria-label="Your account"
          className="flex items-center gap-2.5 rounded-full border border-rule bg-paper py-1 pr-3.5 pl-1 text-sm transition-colors hover:border-ink-2 hover:bg-paper-2 data-[state=open]:border-ink data-[state=open]:bg-paper-2"
        >
          <ProfileAvatar spec={me?.avatar ?? null} name={me?.name ?? name} email={email} className="size-8" />
          <span className="hidden max-w-36 truncate font-medium sm:inline">{(me?.name || name).split(" ")[0]}</span>
          <Chevron className="text-ink-2" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        sideOffset={10}
        className="w-auto min-w-64 border border-rule bg-paper p-1.5 ring-0"
      >
        <DropdownMenuLabel className="flex items-center gap-3 px-2 py-2.5">
          <ProfileAvatar spec={me?.avatar ?? null} name={me?.name ?? name} email={email} className="size-11" />
          <span className="flex min-w-0 flex-col">
            <span className="truncate text-[15px] font-medium text-foreground">{me?.name || name}</span>
            <span className="truncate text-[13px] font-normal text-ink-2">{email}</span>
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem asChild className="px-2 py-2 text-[15px]">
            <Link href="/decks">Your decks</Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild className="px-2 py-2 text-[15px]">
            <Link href="/account">Account and avatar</Link>
          </DropdownMenuItem>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem className="px-2 py-2 text-[15px]" onSelect={() => void signOut()}>
            Sign out
          </DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
