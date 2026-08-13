# Week 3 — The editor, the brand kit, and the v1 acceptance run

**Dates:** Mon 18 Aug – Sun 24 Aug 2026 · **Status:** Phases 08 (web half)–11 complete; v1 done

## What was done this week

Week 2 made the pipeline produce. Week 3 made the whole product path run end to end in a browser, then proved it in one unassisted sitting.

### 1. Phase 08's web half — the Intake screen
- Built the intake screen and the product path: `/new` for the conversation → `Brief`.
- Recorded an open defect from the live pipeline: the provider truncates copy at its `maxLength` cap — and the fix (catch truncated copy before it ships, redraw the scene once).
- Then fixed the truncation at its actual cause: the schema discriminator came last, so the model ran out of budget finishing it.

### 2. Phase 09 — The editor
- Built the editing model: **select → property panel → element-scoped prompt**.
- About 1/5 the cost of a design canvas, and it covers ~90% of edits — the headline and the copy can be changed either by direct property edits or by a prompt scoped to a single element.
- Both paths produce the same patch shape, so the renderer never sees two different edit mechanisms.

### 3. Phase 10 — Brand kit and uploads
- Built the brand kit (`/brand`) and the upload surface — deliberately the only hostile-input surface in v1.
- Uploaded assets are validated and sanitized in an isolated worker; the SVG sanitizer and the isolation tests are part of the gate.

### 4. Phase 11 — Visuals and the Slot
- Built five code-generated visual generators plus the sandboxed Slot — the "90% structure, 10% surprise" runtime.
- Closed the build → save → edit → publish seam so a generated experience survives the full loop.
- Ran the last v1 gate.

### 5. The v1 acceptance run
One sitting, unassisted, against a live API and a production build. A launch page for a fictional clinical-trial scheduling tool, typed as prose:

- taken through the interview to a `Brief`,
- directed into an editable outline,
- built into streamed scenes,
- edited through both the property panel and the element prompt,
- published, presented fullscreen, and embedded.

**All twelve boxes ticked**, including the security-critical ones — `prefers-reduced-motion` collapses all motion, `dir="rtl"` mirrors the layout with no stylesheet change, every image has an alt attribute, and the generations table contains no prompt, no output, and no brief content.

The eval corpus ran to completion for the first time and came back green: **5/5 golden briefs, 7/7 injection payloads, zero failures**.

The run also found two real bugs in code that was already written, reviewed, and tested — both fixed. And it recorded two honest reservations against "you would show it to someone": scene heights don't match a screen, and split layouts are top-anchored. Both are art-direction problems, not code problems — and they are exactly what week 4 went after.

## This week's deliverables
- A complete product path in a browser: intake → outline gate → streamed scenes → edit → publish → present → embed.
- The brand kit and the upload surface with full validation and sanitization.
- Five visual generators and the sandboxed Slot.
- A passing acceptance run and a green eval corpus.

## Next week's plan
- Build art direction #2 — the test that decides whether the central claim was real: if a second art direction needs any renderer *branch*, the abstraction is wrong.
- Prove the variety claim: same scene tree, same 11 primitives, unrecognizably different output, one switch apart.
- Plan v2 — the release that turns the product into a presentation you can present.
