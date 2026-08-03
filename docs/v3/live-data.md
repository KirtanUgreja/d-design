# Live Data

Stats bound to a real source, current on every view. A launch page that says "2,412 teams" and means it today.

## The boundary problem, solved by fetching elsewhere

v1's product boundary is browser-enforced: sandboxed iframes, no network, no storage. Live data is the first feature that wants a network call, and where that call happens decides whether the boundary survives.

**It happens on your infrastructure, never in the page.**

```
Airtable / Notion ──▶ fetch worker ──▶ job worker ──▶ data_sources.last_value
                      (credentials,     (schedules,              │
                       egress only)      writes DB)   baked in at publish ▼
                                                            published page
```

Two workers rather than one, and the split is the same trust boundary the whole backend uses ([../techstack/backend.md](../techstack/backend.md)):

- **The fetch worker makes the call.** It holds the integration credentials, has egress-only networking, no route to the VPC, and no database access. A third-party API returning something hostile — or a compromised integration — lands on a box with nothing to steal.
- **The job worker schedules it and writes the result**, via pg-boss on the database it already has. It never touches the remote response directly.

**A cell value from Airtable is untrusted input**, not internal data. It is user-controlled by definition — anyone who can edit the sheet can write anything into it — so it gets one Zod parse at the boundary, is rendered as text and never as markup, and is length-capped against the art direction's budget like any other copy ([../security/README.md](../security/README.md)).

**Live data adds zero requests to the published page.** No CORS, no API keys in the browser, no third-party script, no fetch from inside a sandbox — the value is baked into the artifact at publish. "Live" means minutes-fresh, which is all a marketing statistic has ever needed.

The page itself is not at zero, and the honest number matters: **a published page makes exactly two requests** — the personalization fields fetch and the analytics beacon ([personalization.md](personalization.md), [../techstack/frontend.md](../techstack/frontend.md)). Live data is not one of them and must not become one.

**Verify in a real browser, not by reading code.** Open a published page with bindings and assert those two requests and nothing else. That test is what proves the boundary held, and it is the reason the CSP names exact paths rather than a host.

## Sources

Airtable and Notion. Where marketing teams already track work, and structured enough to bind to reliably.

```
data_sources  id, kind, credentials_ref, config (jsonb),
              last_fetched_at, last_value (jsonb), last_error
```

Credentials are OAuth tokens, envelope-encrypted under KMS and referenced by id — never present in any scene tree, published page, log line, or error report. **The fetch worker's task role can decrypt integration credentials and nothing else**: not the database password, not the model key, not the signing key ([../techstack/infrastructure.md](../techstack/infrastructure.md)). A compromise of the most exposed container yields the one credential it was actively using.

Refresh runs on a schedule — every 15 minutes is plenty — plus on demand from the editor. Cheap, predictable, and it decouples page views from source rate limits entirely. On-demand refresh is an authenticated, rate-limited action; without that it is an outbound request an attacker can trigger at will.

*Google Sheets is the notable omission.* It has the widest reach and is the cheapest integration of the three, and it was deliberately skipped. Worth revisiting the first time a user asks — Notion databases in particular are awkward as numeric sources.

## Binding

Not a new primitive. A property on existing ones.

```ts
DataBinding {
  sourceId: string;
  path: string;              // "Metrics.ActiveTeams"
  format?: 'number' | 'currency' | 'percent' | 'compact';
  fallback: string;          // required
}
```

| Block | Bindable |
|---|---|
| `Stat` | `value` |
| `SpecTable` | any row `value` |

`Stat.value` becomes `string | DataBinding`. Two blocks, one concept, zero new primitives — the schema barely moves.

`format: 'compact'` renders 2412 as "2.4K". Formatting is locale-aware: separators, currency, and date order follow the locale, so a bound stat reads correctly in German and Japanese without extra authoring.

### `fallback` is required

Not optional, not defaulted. Every binding must state what to show when there is no value, because a marketing page with a blank where a number should be is worse than one with a slightly stale number.

## Failure

Three levels, in order:

1. **Source unreachable** → serve `last_value`. The page does not know anything happened
2. **Never successfully fetched** → serve `fallback`
3. **Path missing from a successful response** → serve `fallback`, flag the binding in the editor

A published page never shows a blank, an error, or a loading state for a bound value. It shows the best number available and says nothing.

The editor is where failure is visible: a bound stat that is stale beyond a threshold, or erroring, is flagged with the last successful fetch time. Notify the publisher on sustained failure — a launch page quietly serving a three-week-old number is the actual bad outcome, and it is invisible from the page itself.

## What this is not

Not a dashboard. Not charts. Not queries, filters, aggregation, or joins.

A binding reads one value from one path and renders it as text. Anything more is a data product wearing a presentation's clothes — and it re-opens the boundary this design just closed by moving the fetch server-side.

## Verification

- Published page with bindings makes the same two requests as any other page and no more — asserted in a real browser
- Kill the source → page serves last good value, unchanged to the viewer
- Never-fetched binding → fallback renders, nothing blank
- Bad path → fallback renders, editor flags it
- Bound stat formats correctly in `de` and `ja`
- Credentials appear in no scene tree, no page source, no client bundle, no log, no error report
- A cell containing markup renders as text
- A cell containing 4,000 characters is capped, not rendered into the layout
