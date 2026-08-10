# Phase 23 — Phone remote

> Advance your own slides from your phone while you walk around the room. Built last, deliberately, because it is the only live-room feature that needs a server — which makes it the only one that cannot work offline.

**Depends on:** [10](10-slides-mode.md), [19](19-presenter-view.md) · **Blocks:** — · **Spec step:** presentation delta

**Build this last and be willing not to build it.** Every other feature in the presentation set degrades gracefully. This one either has a live connection or it is a dead phone in someone's hand during a pitch.

---

## Search

**Read first**

- [../presentation.md](../presentation.md) → "The live room", specifically the paragraph naming the offline contradiction
- [20](20-offline-and-export.md) → what the offline bundle does *not* carry, and why the download says so
- [../../security/tenancy-and-data.md](../../security/tenancy-and-data.md) → a pairing code is an authorisation grant, so rule 10 applies: **anything that grants, fails closed**
- [../../techstack/infrastructure.md](../../techstack/infrastructure.md) → whether a persistent connection is affordable in the stack that exists when this is built

**Grep for**

- `web/src/features/present/channel.ts` → [19](19-presenter-view.md)'s `BroadcastChannel` sync. The phone is a **third participant in an existing protocol**, not a new one. If it needs its own message shape, 19's protocol was under-designed
- `web/src/features/present/fullscreen.tsx` → the advance logic. A remote message is the same advance an arrow key produces, and it must not be a second path
- Auth tables in `web` (Drizzle) → there is no auth in v2. A pairing code is therefore the **only** thing standing between a stranger and someone's live deck

**Verify externally**

- Whether a plain SSE stream plus a small POST endpoint is sufficient, versus a WebSocket. **SSE plus POST is the ponytail answer** — one direction each, no upgrade handshake, no sticky-session infrastructure
- Mobile browser behaviour when the screen locks or the app backgrounds mid-talk, and how quickly a connection re-establishes. This is the failure that actually happens
- Whether the deployment target at build time supports long-lived connections at all

---

## Make

```
api/features/present/
  pair.py              short-lived pairing codes
  channel.py           SSE out, POST in
web/src/features/present/
  remote.tsx           the phone page: prev, next, current slide, notes
```

### Pairing

The presenter's deck shows a short code. The phone opens a URL, enters it, and joins. The code is **short-lived, single-use, and scoped to one presentation session** — not to the deck, and never to the account.

Three properties, all of which are the whole security design at a point in the product where there is no auth:

- **Expires in minutes, not hours.** A code on a projector is a code the whole room can read
- **One phone at a time.** A second pairing displaces the first and the deck says so on screen
- **Advance only.** The remote can move slides. It cannot edit, publish, delete, download, or read anything but the current slide and its notes

That last one is the containment. If pairing is defeated entirely, the attacker's total capability is being annoying with someone's slides in a room they are standing in — which is recoverable — rather than reaching the deck, the account, or the tenant.

### The phone page

Previous, next, the current slide number, and the speaker notes. Notes on the phone is most of why this feature is wanted at all — it is presenter view in your hand when there is no second screen, which is most rooms.

**Notes on a phone are still not an audience surface**, but the threat model is different from [19](19-presenter-view.md)'s: the risk is a phone being handed around or glanced at, not a URL leaking. Same rule, weaker enforcement, and worth stating rather than assuming.

### The offline contradiction, stated in the product

A downloaded bundle has no server, so it has no remote. This is not a bug to work around; it is what "offline" means.

The bundle's UI says so plainly, at download time and again in the presenting UI. **A presenter must not discover this on stage.** The one thing worse than a missing feature is a feature the user believed they had.

---

## Verify

**The gate** — green.

**It works**

- [ ] Pair a phone, advance the whole deck from it, both directions
- [ ] The phone shows the current slide number and its notes
- [ ] A remote advance goes through the same advance path an arrow key does. **Greppable** — no second path
- [ ] Locking the phone, unlocking it, and backgrounding the browser all recover without re-pairing
- [ ] The deck advances correctly when the laptop is also fullscreen on an external display

**It fails safely**

- [ ] An expired code is refused. A reused code is refused. A guessed code is refused, and guessing is rate-limited
- [ ] A second phone displaces the first, and the deck says so on screen
- [ ] The remote cannot edit, publish, delete or download. **Test each of these explicitly against the endpoint**, not against the UI
- [ ] Connection loss shows an honest state on the phone rather than silently doing nothing. Rule 10 — a permissive default here is a dead clicker
- [ ] Keyboard and clicker keep working with no phone paired, and keep working when a paired phone drops

**Offline**

- [ ] The downloaded bundle has no remote UI at all, and its download page says why
- [ ] No pairing endpoint, code, or connection attempt exists in the bundle's bytes

---

## Skipped

| Not built | Trigger |
|---|---|
| A native app | Never for this. A web page that pairs in five seconds beats an install |
| Laser pointer / on-slide annotation | If presenting reveals the need. It is a second interaction model on the audience surface |
| Audience-facing phone features — polls, Q&A | A different product. Do not let this endpoint become that |
| Remote across the internet (present to a room you are not in) | Video calls already solve this |
| Offline pairing over local network | Real work, real security surface, and it defeats the simplicity that makes the bundle trustworthy |
| Multiple paired phones | One presenter, one remote |

---

## Exit gate

- [ ] Pair, advance both ways, see notes, recover from lock and background
- [ ] Codes are short-lived, single-use, session-scoped, rate-limited
- [ ] The remote's total capability is advance and read-current. Verified at the endpoint
- [ ] One phone at a time, displacement visible on the deck
- [ ] Keyboard and clicker unaffected in every state
- [ ] The offline bundle contains no remote and says why
- [ ] The gate is green
