<p align="center">
  <img src=".github/hero.jpg" alt="d-design: every deck, its own designer" width="100%">
</p>

<h1 align="center">d-design</h1>

<p align="center">
  <b>An open-source AI presentation maker whose edge is design.</b><br>
  Type a brief. Get a deck that looks designed by a person and says something,<br>
  as <b>one offline <code>.html</code> file</b> (and a PDF).
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-black" alt="MIT license"></a>
  <a href="https://github.com/KirtanUgreja/d-design/actions/workflows/gate.yml"><img src="https://github.com/KirtanUgreja/d-design/actions/workflows/gate.yml/badge.svg" alt="gate"></a>
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-black" alt="PRs welcome"></a>
</p>

Most AI deck tools fill templates, so every deck looks the same. d-design has no templates. The model writes each slide in real HTML and CSS inside a design system made for that deck. Then every slide is rendered in Chromium and measured before you see it. Every number traces to you or a cited source, or it is flagged.

## Deploy your own on Railway

You need a [Railway](https://railway.com) account and an [OpenRouter](https://openrouter.ai/keys) key.

```bash
git clone https://github.com/KirtanUgreja/d-design.git && cd d-design
brew install railway        # or: npm i -g @railway/cli
railway login
./scripts/deploy-railway.sh
```

The script asks for your OpenRouter key and the emails allowed to sign up. Then it creates everything: two Postgres databases, the `api`, `worker` and `web` services, their variables, a secret and a public URL. It prints the URL when it is done. The first build takes about 5 minutes.

To ship new code later, run the same command. It sees the project exists and only redeploys. If a first run stops halfway, run it again and it carries on.

**On Railway's free plan,** only 3 services fit, and the two databases would make 5. Bring your own Postgres instead: create two databases (for example on [Neon](https://neon.tech)'s free tier), then run `APP_DATABASE_URL=... AUTH_DATABASE_URL=... ./scripts/deploy-railway.sh`. The script then adds no database of its own. On the Hobby plan, it creates both for you.

## Pick your model

Every model call goes through [OpenRouter](https://openrouter.ai/models), so any model id it lists works. Set one variable:

```bash
MODEL=deepseek/deepseek-v4.1-flash                                     # in .env, for a local run
railway variable set --service worker MODEL=deepseek/deepseek-v4.1-flash   # on Railway
```

`MODEL` sets every text role. To tune one role, set `MODEL_WRITING` (research and the storyline), `MODEL_DESIGN` (the slide designer and improver) or `MODEL_CHEAP` (the interview and speaker notes); a role setting beats `MODEL`. `MODEL_IMAGE` picks the slide-image model, and an empty value turns images off. With nothing set, the pinned defaults in [`api/settings.py`](api/settings.py) apply. Cost is metered from OpenRouter's own figures, so the per-user daily cap (`DAILY_CAP_USD`, default $3) works with any model.

## How it makes a deck

| Step | What happens | Where |
|---|---|---|
| Brief → questions | A few targeted questions, including what the product does; skippable | `api/engine/content/interview.py` |
| **1. Research** | Two web searches at once: a **product file** (what it does, for whom, features, pricing, traction, competitors) and the **market evidence** the story needs. Only what a returned page quotes is kept | `api/engine/studio/research.py` |
| **2. Outline** | One argument, a claim and a short explanation per slide, points, a figure, a chart from approved facts or a drawn product visual. Every number traces to you or a source, or is held for your decision | `api/engine/studio/outline.py` |
| **Style** | One of **8 visual languages**, then a generated palette (built around **your brand colour** if you give one) and a type pairing. Three thumbnails of *your* slides show it before you pay for a build | `api/engine/design/`, `api/library/languages/` |
| **3. Art director → designer** | One call plans every slide's composition for the whole deck (hero, field, crop, scale), so no two neighbours look alike. Then a designer writes each slide in real HTML, CSS and flat SVG, inside the deck's tokens. No templates, no reference library | `api/engine/studio/direct.py`, `design.py` |
| **4. Improver** | A creative director **looks at a screenshot of each rendered slide**, critiques it and redesigns it to be bolder. The redesign is kept only if QA measures it no worse | `api/engine/studio/improve.py` |
| **5. Deck review** | The whole deck on one sheet, judged as a piece: rhythm, look-alikes, the tells of AI-made slides. The two weakest slides go back to the improver with a note | `api/engine/studio/review.py` |
| **Check** | Every slide is rendered in Chromium and measured: overflow, collisions, contrast (WCAG + APCA), type size, empty blocks. A defect gets two targeted repairs, then a code-built layout, then a visible flag. Nothing broken ships silently | `api/engine/qa/`, `api/engine/studio/build.py` |
| Edit → export | Edit text, reorder, recolour, fit, undo; present, send (one offline file, zero network requests) or PDF | `api/worker.py`, `api/engine/export/` |

## Architecture

```
browser ──▶ web (Next.js 16, public) ──private network──▶ api (FastAPI) ──▶ Postgres "app"
              │ Better Auth (email + password,                                   ▲
              │ allowlist) ─▶ Postgres "auth"                                    │
              │ signs a short EdDSA JWT per request                    worker (model key, Chromium)
```

- **web** is the only public service. It never exposes the JWT to the browser: its `/api` proxy mints one per request.
- **api** verifies the JWT against Better Auth's JWKS. It fails closed: an unreachable JWKS is a 401. Every deck route goes through one tenant wrapper, so another user's deck is a 404. A per-user daily spend cap also fails closed. The api holds **no model key** and runs no browser.
- **worker** has no inbound port. It is the only holder of the OpenRouter key and of Chromium, and claims jobs from Postgres with `SKIP LOCKED`.
- **Data:**
  - In Postgres: decks, events, versions, a ledger of every model call's cost per user, and slide files stored by content hash.
  - Better Auth's tables live in their own database, which Python never reads.
- **Hosting:** Railway runs the three services. Postgres is Neon or Railway's own.

## Run it locally

```bash
./scripts/setup.sh          # once: git hooks, Python and web deps, Chromium
cp .env.example .env        # add OPENROUTER_API_KEY and a Postgres URL
./scripts/dev.sh            # api + worker + web → http://localhost:3000
```

`web/.env.local` needs `AUTH_DATABASE_URL` and `BETTER_AUTH_SECRET`. To skip accounts, `cd api && AUTH_DISABLED=1 uv run uvicorn app:serve --factory` serves one local user.

## Tests

```bash
cd api && uv run pytest -q          # about 210 tests, offline: fake models, real Chromium
cd web && pnpm e2e                  # sign-up, sign-in and the token proxy
./scripts/hooks/pre-commit          # ruff, mypy --strict, pytest, eslint, tsc, OpenAPI drift, docs
```

The security tests (`api/tests/test_security.py`) call every route with no session, with a forged token and with another user's session. They also cover the spend cap, including a cap check that itself fails.

## Known limits

- One worker, so builds queue.
- Four visual languages are on (Studio, Frame, Bright, Soft), so looks repeat across many decks.
- Accounts are email and password for an allowlist. There is no password reset by email and no OAuth; a signed-in person changes their password on the account page.

## Contributing

Issues and pull requests are welcome. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md), then [`docs/code-guide.md`](docs/code-guide.md), which explains the code file by file and term by term. The rules every change follows are in [`AGENTS.md`](AGENTS.md). The databases as SQL are in [`db/`](db/README.md). Why things are the way they are is in [`docs/v4/spec.md`](docs/v4/spec.md). Security reports go through [`SECURITY.md`](SECURITY.md).

## License

[MIT](LICENSE). The fonts in `api/library/fonts/` keep their own licenses (SIL Open Font License), included beside each font.
