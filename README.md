<p align="center">
  <img src=".github/hero.jpg" alt="d-design: every deck, its own designer" width="100%">
</p>

<h1 align="center">d-design</h1>

<p align="center">
  <b>The open-source AI deck maker that designs, not templates.</b><br>
  Type a brief. Get a deck that looks made by a designer, as one offline <code>.html</code> file.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-111?style=flat-square" alt="MIT license"></a>
  <a href="https://github.com/KirtanUgreja/d-design/actions/workflows/gate.yml"><img src="https://img.shields.io/github/actions/workflow/status/KirtanUgreja/d-design/gate.yml?branch=main&style=flat-square&label=gate" alt="gate"></a>
  <img src="https://img.shields.io/badge/python-3.13-111?style=flat-square" alt="Python 3.13">
  <img src="https://img.shields.io/badge/next.js-16-111?style=flat-square" alt="Next.js 16">
  <a href="CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-welcome-111?style=flat-square" alt="PRs welcome"></a>
</p>

<p align="center">
  <a href="#-deploy-in-one-command">Deploy</a> ·
  <a href="#-how-it-works">How it works</a> ·
  <a href="#-pick-your-model">Models</a> ·
  <a href="#-architecture">Architecture</a> ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

<br>

<table>
  <tr>
    <td width="33%" valign="top">
      <h3>🎨 Designed, not filled</h3>
      No templates. The model writes every slide in real HTML and CSS, inside a design system made for that deck.
    </td>
    <td width="33%" valign="top">
      <h3>🔍 Checked before you see it</h3>
      Every slide is rendered in Chromium and measured for overflow, collisions and contrast. Broken slides get fixed or flagged.
    </td>
    <td width="33%" valign="top">
      <h3>📎 Every number has a source</h3>
      Figures trace to your brief or a cited page. Anything else is held for you to approve.
    </td>
  </tr>
</table>

<p align="center">
  <img src=".github/gallery.jpg" alt="Slides d-design made, unedited" width="100%">
</p>

## 🚀 Deploy in one command

You need a [Railway](https://railway.com) account and an [OpenRouter](https://openrouter.ai/keys) key.

```bash
git clone https://github.com/KirtanUgreja/d-design.git && cd d-design
railway login
./scripts/deploy-railway.sh
```

It asks for your key and who may sign up, then builds the databases, the three services and a public URL. Run it again to ship new code.

> [!TIP]
> **On Railway's free plan** (3 services), bring two free [Neon](https://neon.tech) databases:
> `APP_DATABASE_URL=... AUTH_DATABASE_URL=... ./scripts/deploy-railway.sh`

## ✨ How it works

```mermaid
flowchart LR
    A([✍️ Brief]) --> B[Research<br><sub>cited facts</sub>]
    B --> C[Outline<br><sub>one argument</sub>]
    C --> D[Look<br><sub>palette · type</sub>]
    D --> E[Design<br><sub>HTML + CSS</sub>]
    E --> F[Improve<br><sub>sees a screenshot</sub>]
    F --> G{QA in<br>Chromium}
    G -- defect --> E
    G -- pass --> H([📦 One .html file])

    classDef io fill:#111,stroke:#111,color:#fff
    classDef step fill:#f5f1ea,stroke:#d6cfc4,color:#111
    classDef check fill:#ffe9d6,stroke:#f08a4b,color:#111
    class A,H io
    class B,C,D,E,F step
    class G check
```

<details>
<summary><b>Each step, and where it lives in the code</b></summary>

<br>

| Step | What happens | Code |
|---|---|---|
| Interview | A few targeted questions; skippable | `api/engine/content/interview.py` |
| Research | A product file and the market evidence; only quoted facts are kept | `api/engine/studio/research.py` |
| Outline | A claim per slide; every number traces to you or a source | `api/engine/studio/outline.py` |
| Look | One of 8 visual languages, a palette around your brand colour, a type pairing | `api/engine/design/` |
| Design | An art director plans the deck; a designer writes each slide | `api/engine/studio/direct.py`, `design.py` |
| Improve | A creative director critiques a screenshot and redesigns; kept only if QA agrees | `api/engine/studio/improve.py` |
| Review | The whole deck judged as one piece; the two weakest slides go back | `api/engine/studio/review.py` |
| QA | Overflow, collisions, contrast (WCAG + APCA), type size; two repairs, then a flag | `api/engine/qa/` |
| Export | Present, one offline file with zero network requests, or PDF | `api/engine/export/` |

</details>

## 🧠 Pick your model

Any [OpenRouter model](https://openrouter.ai/models) works. One variable switches them all:

```bash
MODEL=deepseek/deepseek-v4.1-flash                                         # .env, local
railway variable set --service worker MODEL=deepseek/deepseek-v4.1-flash   # Railway
```

| Variable | Sets | Default |
|---|---|---|
| `MODEL` | every text role at once | the pins below |
| `MODEL_WRITING` | research and the storyline | `anthropic/claude-sonnet-5.5` |
| `MODEL_DESIGN` | the designer and improver | `anthropic/claude-sonnet-5.5` |
| `MODEL_CHEAP` | the interview and speaker notes | `anthropic/claude-haiku-5.5` |
| `MODEL_IMAGE` | slide images (empty = off) | `google/gemini-3.1-flash-lite-image` |
| `DAILY_CAP_USD` | spend cap per user per day | `3` |

## 🏗 Architecture

```mermaid
flowchart LR
    U((👤 Browser)) --> W

    subgraph R[Railway]
        W[<b>web</b><br><sub>Next.js · Better Auth</sub>]
        A[<b>api</b><br><sub>FastAPI · no model key</sub>]
        K[<b>worker</b><br><sub>model key · Chromium</sub>]
    end

    subgraph P[Postgres]
        AD[(auth)]
        PD[(app)]
    end

    W -- "JWT per request" --> A
    W --> AD
    A --> PD
    K -- "claims jobs" --> PD
    K -- "model calls" --> OR([OpenRouter])

    classDef pub fill:#111,stroke:#111,color:#fff
    classDef svc fill:#f5f1ea,stroke:#d6cfc4,color:#111
    classDef db fill:#e8f0ff,stroke:#7a9cff,color:#111
    classDef ext fill:#fff,stroke:#bbb,color:#111,stroke-dasharray:4 3
    class W pub
    class A,K svc
    class AD,PD db
    class U,OR ext
    style R fill:transparent,stroke:#999,stroke-dasharray:5 4
    style P fill:transparent,stroke:#7a9cff,stroke-dasharray:5 4
```

- **web** is the only public service. Its `/api` proxy mints a short EdDSA JWT per request, which the browser never sees.
- **api** checks that JWT and fails closed. Another user's deck is a 404.
- **worker** has no inbound port. It alone holds the model key and the browser.

<details>
<summary><b>Run it locally</b></summary>

<br>

```bash
./scripts/setup.sh          # git hooks, Python and web deps, Chromium
cp .env.example .env        # add OPENROUTER_API_KEY and a Postgres URL
./scripts/dev.sh            # api + worker + web → http://localhost:3000
```

`web/.env.local` needs `AUTH_DATABASE_URL` and `BETTER_AUTH_SECRET`. To skip accounts: `cd api && AUTH_DISABLED=1 uv run uvicorn app:serve --factory`.

</details>

<details>
<summary><b>Tests</b></summary>

<br>

```bash
cd api && uv run pytest -q      # ~210 tests, offline: fake models, real Chromium
cd web && pnpm e2e              # sign-up, sign-in, the token proxy
./scripts/hooks/pre-commit      # the whole gate
```

The security tests call every route with no session, a forged token and another user's session.

</details>

<details>
<summary><b>Known limits</b></summary>

<br>

- One worker, so builds queue.
- Four of the eight visual languages are on, so looks repeat across many decks.
- Email and password for an allowlist; no OAuth, no reset by email.

</details>

## 🤝 Contributing

Issues and PRs are welcome. Start with [`CONTRIBUTING.md`](CONTRIBUTING.md) and the [code guide](docs/code-guide.md). Security reports go to [`SECURITY.md`](SECURITY.md).

## 📄 License

[MIT](LICENSE). The bundled fonts keep their own SIL Open Font License.
