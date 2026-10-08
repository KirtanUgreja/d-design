"use client";
// Your decks: GET /api/decks (through the /api proxy, so only this user's),
// newest first, each a link to its live page.
import Link from "next/link";
import { useEffect, useState } from "react";

import { ProfileAvatar, useMe } from "@/components/avatar";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyTitle } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { err, ok, type Result } from "@/lib/result";

interface DeckRow {
  id: string;
  title: string;
  status: string;
  at: number | null;
}

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === "object" && v !== null && !Array.isArray(v);
const text = (v: unknown): string => (typeof v === "string" ? v : "");

const STATUS_LABEL: Record<string, string> = {
  brief: "Brief",
  interview: "Questions",
  outline: "Outline",
  approve: "Outline",
  building: "Building",
  ready: "Ready",
  error: "Failed",
  aborted: "Stopped",
};

function row(v: unknown): DeckRow | null {
  if (!isObj(v) || typeof v.id !== "string") return null;
  const story = isObj(v.storyline) ? v.storyline : {};
  const brief = isObj(v.brief) ? v.brief : {};
  const title = text(v.title) || text(story.governing_thought) || text(brief.prompt) || "Untitled deck";
  // ponytail: the API sends no timestamp yet, so its own order stands unless
  // one arrives (created_at or updated_at, ISO 8601).
  const stamp = Date.parse(text(v.updated_at) || text(v.created_at));
  return { id: v.id, title, status: text(v.status), at: Number.isNaN(stamp) ? null : stamp };
}

async function loadDecks(): Promise<Result<DeckRow[]>> {
  let res: Response;
  try {
    res = await fetch("/api/decks", { headers: { accept: "application/json" } });
  } catch {
    return err("We can't reach the deck service. Is it running?");
  }
  const body: unknown = await res.json().catch(() => null);
  if (!res.ok) return err(isObj(body) && typeof body.error === "string" ? body.error : "We can't reach the deck service.");
  if (!Array.isArray(body)) return err("The deck service sent something we couldn't read.");
  const rows = body.map(row).filter((r): r is DeckRow => r !== null);
  if (rows.every((r) => r.at !== null)) rows.sort((a, b) => (b.at ?? 0) - (a.at ?? 0));
  return ok(rows);
}

export function DecksList({ user }: { user: { name: string; email: string } }) {
  const me = useMe();
  const [decks, setDecks] = useState<Result<DeckRow[]> | null>(null);

  useEffect(() => {
    let live = true;
    void loadDecks().then((r) => live && setDecks(r));
    return () => {
      live = false;
    };
  }, []);

  return (
    <div className="flex flex-col gap-8 pt-10">
      <div className="flex items-center gap-4">
        <ProfileAvatar spec={me?.avatar ?? null} name={me?.name || user.name} email={user.email} size="lg" />
        <h1 className="font-display text-3xl tracking-tight">Your decks</h1>
      </div>
      {decks === null ? (
        <ul className="flex flex-col gap-3" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <li key={i}>
              <Skeleton className="h-12 w-full" />
            </li>
          ))}
        </ul>
      ) : !decks.ok ? (
        <Alert variant="destructive">
          <AlertDescription>{decks.error}</AlertDescription>
        </Alert>
      ) : decks.value.length === 0 ? (
        <Empty className="border border-rule">
          <EmptyHeader>
            <EmptyTitle>No decks yet</EmptyTitle>
            <EmptyDescription>Type a brief and your first deck shows up here.</EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button asChild>
              <Link href="/">Start a deck</Link>
            </Button>
          </EmptyContent>
        </Empty>
      ) : (
        <ul className="flex flex-col border-t border-rule">
          {decks.value.map((d) => (
            <li key={d.id} className="border-b border-rule">
              <Link href={`/d/${d.id}`} className="group flex items-baseline justify-between gap-6 py-4">
                <span className="truncate group-hover:underline">{d.title}</span>
                {d.status && <Badge variant="outline">{STATUS_LABEL[d.status] ?? d.status}</Badge>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
