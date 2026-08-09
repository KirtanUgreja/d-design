# Phase 06 — Version history

> Not a feature. The safety net that makes every transformation after it acceptable to ship. One-click reskin without undo is a feature that eats people's work.

**Depends on:** [04](04-three-art-directions.md) · **Blocks:** [07](07-reskin.md) · **Spec step:** 6

---

## Search

**Read first**

- [../transformations.md](../transformations.md) → "Version history" — the snapshot shape, the retention rule, and why restoring is itself undoable
- [../spec.md](../spec.md) → "Persistence delta"

**Grep for**

- `web/src/features/editor/store.ts` — the Zustand `past`/`future` stacks and `MAX_HISTORY`. That is **keystroke-granularity undo within a session** and it stays exactly as it is. Snapshots are a different thing at a different granularity, and conflating them produces a history panel with a hundred entries called "typed a character"
- `api/features/publish/__init__.py` — `replace_experience`. Every destructive write goes through one function, which is what makes "snapshot before" a single insertion point rather than an audit
- `api/migrations/versions/0007_snapshots.py` — the table, from phase 00

**Verify externally** — nothing.

---

## Make

```
api/features/history/
  __init__.py              snapshot, list, restore
  history_data.py          SQLAlchemy, snapshots only
  test_history.py
api/routes/history.py
web/src/features/history/
  history-panel.tsx        the list, the labels, restore
  history.ts              the client
```

### What a snapshot is

```
snapshots  id, experience_id, owner_id,
           scenes jsonb, art_direction jsonb, motion_vocabulary, mode,
           label, trigger, created_at
```

**The whole tree, not a patch.** A scene tree is a few KB of JSON; storing fifty whole copies costs less than reconstructing state from a patch log, and it answers the only question users actually ask — *put it back the way it was before I clicked that.*

It captures all four axes, not just the scenes. Restoring a tree without restoring the art direction it was authored against produces a restore that does not look like what the user remembers, which is worse than no restore at all.

### When one is taken

**Automatically, before every destructive action:** reskin, scene regenerate, bulk edit, mode switch, publish. Plus user-named checkpoints, unlimited.

`trigger` records which. That field is what makes the panel readable — "before reskin to Bold Brutalist" is a thing a person can navigate by, where a timestamp is not.

Retain the last 50 auto-snapshots per experience; named ones forever. Pruning happens at insert, in the same transaction, so the table cannot grow while nobody is looking.

### Restoring is itself undoable

**Restore snapshots the present first, then writes the old state back.** Two rows, one transaction. A user who restores the wrong thing must be able to restore back, and the version of this feature that cannot is the version that turns one mistake into two.

### The insertion point

Every destructive write already goes through `replace_experience`. **Snapshot there, not at each call site** — a snapshot rule enforced at five call sites is a snapshot rule with four bugs in it waiting for someone to add a sixth.

The parameter is the trigger label, which means the caller says *why* and never *whether*.

---

## Verify

**The gate** — green.

**Snapshots**

- [ ] Every destructive action produces exactly one snapshot, with the right trigger label. Assert on the count as well as the presence — a double-snapshot is how a fifty-entry retention window becomes twenty-five
- [ ] A snapshot captures scenes, art direction *with version*, motion vocabulary, and mode
- [ ] The 51st auto-snapshot prunes the oldest, in the same transaction
- [ ] Named snapshots are never pruned, including when there are more than fifty of them

**Restore**

- [ ] Restore writes the snapshot back and the tree is byte-identical to what was captured
- [ ] Restore snapshots the present first, so restoring is undoable
- [ ] Restoring a snapshot whose art direction version no longer resolves fails closed with a message, rather than restoring a tree into an art direction that is not there

**Security** ([../../security/testing.md](../../security/testing.md))

- [ ] A second user cannot list, read, or restore another user's snapshots. Through `as_user()`, and through the route with the other user's session
- [ ] Restoring another user's snapshot id into your own experience is refused — the check is on the snapshot's owner, not on the experience's

**Human**

- [ ] Reskin, edit, reskin again, then open the panel. The list has to be legible as a story of what you did. If it reads as a log, the trigger labels are wrong

---

## Skipped

| Not built | Trigger |
|---|---|
| Full undo/redo at keystroke granularity, persisted | Not planned. The in-session store already covers it, and persisting it is editor-grade work for a need milestone snapshots cover |
| Diffing two snapshots | When a user asks what changed. Restore answers "put it back"; diff answers a question nobody has asked yet |
| Branching from a snapshot | v3 at the earliest. It turns history into version control, with the merge problem attached |
| Snapshotting published artifacts | Publishing already freezes an artifact on disk, and the AD version is pinned. A snapshot of a frozen thing is a copy of a copy |

---

## Exit gate

- [ ] Every destructive write snapshots first, from one insertion point
- [ ] A snapshot captures all four axes, including the art direction's version
- [ ] Restore is byte-exact and is itself undoable
- [ ] Retention prunes to 50 auto-snapshots and never prunes a named one
- [ ] Cross-tenant read and restore are both refused
- [ ] The gate is green
