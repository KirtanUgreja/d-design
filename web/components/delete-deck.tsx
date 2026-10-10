"use client";
// Delete a deck at any stage, after one confirmation (owner, 2026-10-10: a
// half-done deck could not be removed). A build is stopped first; the API
// refuses while the worker is on it and says so.
import { useState } from "react";

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
import { api } from "@/lib/api/client";
import { cn } from "@/lib/utils";

export function DeleteDeck({
  id,
  name,
  onDeleted,
  className,
}: {
  id: string;
  name: string;
  onDeleted: () => void;
  className?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove(e: React.MouseEvent) {
    e.preventDefault(); // keep the dialog open until it has worked
    setBusy(true);
    const done = await api.deleteDeck(id);
    setBusy(false);
    if (!done.ok) return setError(done.error);
    onDeleted();
  }

  return (
    <AlertDialog onOpenChange={() => setError(null)}>
      <AlertDialogTrigger asChild>
        <Button variant="link" size="sm" className={cn("h-auto px-0 text-ink-2 hover:text-flag", className)}>
          Delete
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete {name ? `“${name}”` : "this deck"}?</AlertDialogTitle>
          <AlertDialogDescription>
            Its slides, outline, screenshots and history go with it. This can&apos;t be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error && <p className="text-sm text-flag">{error}</p>}
        <AlertDialogFooter>
          <AlertDialogCancel>Keep it</AlertDialogCancel>
          <AlertDialogAction variant="destructive" disabled={busy} onClick={(e) => void remove(e)}>
            {busy ? "Deleting…" : "Delete deck"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
