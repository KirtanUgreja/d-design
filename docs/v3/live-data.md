# Live Data

Stats bound to a real source, current on every view. A launch page that says "2,412 teams" and means it today.

## The boundary problem, solved by fetching elsewhere

v1's product boundary is browser-enforced: sandboxed iframes, no network, no storage. Live data is the first feature that wants a network call, and where that call happens decides whether the boundary survives.

**It happens on your server, never in the page.**

```
Airtable / Notion ──▶ your server (scheduled) ──▶ data_sources.last_value
                                                          │
                                          baked in at render ▼
                                                    published page
```

The published page makes **zero outbound requests**. No CORS, no API keys in the browser, no third-party script, no fetch from inside a sandbox. The boundary is untouched, and "live" means minutes-fresh — which is all a marketing statistic has ever needed.

**Verify this in devtools, not by reading code.** Open a published page with live data bound and confirm the network tab shows nothing beyond your own assets. It is the single check that proves the boundary held.

## Sources

Airtable and Notion. Where marketing teams already track work, and structured enough to bind to reliably.

```
data_sources  id, kind, credentials_ref, config (jsonb),
              last_fetched_at, last_value (jsonb), last_error
```

Credentials are OAuth tokens held server-side, referenced by id, never present in any scene tree or published page.

Refresh runs on a schedule — every 15 minutes is plenty — plus on demand from the editor. Cheap, predictable, and it decouples page views from source rate limits entirely.

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

- Published page with bindings makes zero outbound requests — checked in devtools
- Kill the source → page serves last good value, unchanged to the viewer
- Never-fetched binding → fallback renders, nothing blank
- Bad path → fallback renders, editor flags it
- Bound stat formats correctly in `de` and `ja`
- Credentials appear in no scene tree, no page source, no client bundle
