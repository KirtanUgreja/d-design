# Infrastructure

Where everything runs, and how the security requirements stop being promises and become configuration.

## The repos

Two, split on the trust boundary rather than on the job boundary.

```
d-design           Next.js app · renderer · pipeline · job worker · schema
d-design-fetch     the network-isolated fetch worker
```

**Only the fetch worker gets its own repo**, because it is the only component whose isolation is a security property. The job worker ships from the app repo — it needs the schema, the data modules, and eventually the renderer, and separating it would buy nothing while duplicating everything.

The `Scene` schema is published as **`@d-design/schema`**, a private npm package, for the small amount the fetch worker needs. The version pin makes drift explicit rather than silent — the failure mode of a git submodule is a worker quietly sitting on an old commit, which is precisely the drift the one-source-of-truth rule exists to prevent ([../coderules/typescript.md](../coderules/typescript.md)).

The renderer is **not** shared with the fetch worker, and never should be — that container handles hostile input, and page-making capability does not belong inside the quarantine. The job worker has it by virtue of shipping from the app repo, which is what lets publishing and the visual verification loop run there without a function-timeout ceiling ([backend.md](backend.md), [pipeline-tools.md](pipeline-tools.md)).

## AWS topology

The reason to be on AWS is that [../security/infrastructure.md](../security/infrastructure.md)'s central claim — *"the process doing the fetching cannot reach anything worth reaching"* — becomes a subnet and a security group rather than a sentence in a document.

```
VPC
├── private subnet (app tier)
│   ├── ECS: job worker      → RDS, Secrets Manager, model API
│   └── RDS Proxy → Aurora Postgres
│
└── isolated subnet (quarantine)
    └── ECS: fetch worker
        · security group: NO ingress, egress 0.0.0.0/0 only
        · NO route to the app subnet
        · NO route to 169.254.169.254 (metadata) — IMDSv2 disabled on the task
        · task role: one KMS key for integration credentials, nothing else
```

**ECS Fargate**, one task definition per worker. Fargate over App Runner because App Runner hides exactly the networking that is the point; over Lambda because pg-boss wants a persistent process and 15 minutes does not fit a 12-locale transcreation run.

The socket-level unreachability test in [../security/testing.md](../security/testing.md) — *from inside the worker, the metadata IP and a VPC host are unreachable* — is now a test of this configuration rather than of application code. That is the whole point: it asserts the network, and the network cannot be bypassed by a parsing bug.

### The fetch worker's contents

Headless Chromium via **Playwright** for URL screenshots, plus `pdf.js`/`unpdf` for document text extraction and `sharp` for image re-encoding. In other words, **every CVE-rich dependency in the project lives in the one container that has nothing to steal.** That placement is deliberate and it is the mitigation for the parser risk flagged in [../security/platform-and-packages.md](../security/platform-and-packages.md).

One documented fallback: if a PDF parser advisory lands and there is no patch, Opus 5 reads PDFs natively — text, layout, and charts in one pass, no parser dependency at all. Slower and it costs tokens; available immediately.

## Delivery

```
app.<domain>      → Vercel                  editor, API, sessions
pages.<domain>    → CloudFront ← S3         published experiences (static)
assets.<domain>   → CloudFront ← S3         uploads and generated files
```

**Published experiences are static objects, not routes.** Publishing renders HTML in the app and writes it to S3; CloudFront serves it. There is no origin server behind `pages.<domain>`.

That has three consequences worth stating:

- **Origin separation becomes physical.** An XSS in published content cannot reach an app session because there is no shared infrastructure at all, not merely a different cookie scope.
- **Web cache deception nearly vanishes.** The attack needs the origin to be *more lenient* than the cache about what a URL means. `/r/<token>/x.css` against S3 is a 404 from a key that does not exist — there is no router to be lenient. The controls in [../security/platform-and-packages.md](../security/platform-and-packages.md) still apply to the `/r/` fields endpoint, which is a Vercel route.
- **A viral launch page costs pennies** and cannot exhaust a connection pool, which is what [../coderules/performance.md](../coderules/performance.md) meant by "static after render."

**Cache-Control is explicit per object type**: long-lived and immutable for content-hashed assets, short with revalidation for published HTML so a republish propagates. Invalidate on publish rather than relying on TTL expiry.

`assets.<domain>` serves with `Content-Type` set by the server and `X-Content-Type-Options: nosniff`. Uploads are presigned direct-to-S3, but **the object is not servable until the fetch worker has verified magic bytes and re-encoded it** — an upload lands in a quarantine prefix and moves to the public prefix only after processing. Presigned uploads without that step is uploading arbitrary bytes to your own CDN.

### Custom domains

**ACM certificates with CloudFront SNI.** DNS validation pairs with the TXT ownership challenge already specified in [../security/content-and-web.md](../security/content-and-web.md) — one verification step serving two purposes.

Watch the per-distribution SAN limit. Many customer domains means either multiple distributions or a different strategy, and that is a scaling decision to make deliberately at maybe fifty domains, not to be surprised by. **Cloudflare for SaaS is the documented escape hatch** if custom domains become a real business — it is purpose-built for this and has no such limit.

The dangling-DNS rules from [../security/content-and-web.md](../security/content-and-web.md) apply in both directions, including to your own records.

## Secrets

**AWS Secrets Manager + KMS.** KMS is what the envelope encryption in [../security/tenancy-and-data.md](../security/tenancy-and-data.md) already assumed; being on AWS makes it the obvious implementation rather than a new dependency.

Access is by task role, which is the part that matters: **the fetch worker's role can decrypt integration credentials and nothing else.** Not the database password, not the model key, not the signing key. A compromise of the most exposed container yields the one secret it was actively using.

Vercel environment variables hold the app's own configuration. GitHub Actions authenticates to AWS via **OIDC** — no long-lived AWS keys in GitHub, which is one of the more common ways a pipeline becomes an entry point.

## Infrastructure as code

**Terraform / OpenTofu.** The reason is not tooling preference: the fetch worker's isolation *is* the security control, and in the console it is undocumented state that nobody can review and that drifts silently. In Terraform it is a diff — and "no route from the quarantine subnet to the app subnet" becomes a line someone can read in a pull request.

Everything in it: VPC, subnets, route tables, security groups, ECS services and task roles, RDS, S3 buckets and policies, CloudFront distributions and cache policies, ACM, KMS keys and grants, Secrets Manager.

The cache-key policy belongs in Terraform specifically. It is a security control now ([../security/platform-and-packages.md](../security/platform-and-packages.md)), and a security control configured by hand in a console is one you cannot prove is still correct.

## CI/CD

**GitHub Actions**, both repos.

| | |
|---|---|
| **App repo** | Gate → Vercel deploys on push natively. Job-worker image builds to ECR and updates the Fargate service |
| **Fetch worker repo** | Gate → image to ECR → Fargate service update |
| **Both** | typecheck, lint, format, Vitest, dependency advisory check, duplication report ([../coderules/ai-authorship.md](../coderules/ai-authorship.md)) |
| **App repo, additionally** | Playwright suite including the security assertions, and the build-output grep for key-shaped strings |

Terraform runs `plan` on PR and `apply` on merge to main, gated on review. An infrastructure change that alters a security group should be as visible as a code change that alters an auth check — more so, since nothing type-checks it.

## Local development

```yaml
# docker-compose.yml
postgres     # the real database
minio        # S3-compatible object storage
localstack   # KMS and Secrets Manager
```

Everything runs offline. The point is not convenience — it is that **`storage.ts` talks to the S3 API locally and in production**, so the one abstraction with a planned second implementation ([../v1/spec.md](../v1/spec.md)) has one implementation after all. MinIO is not a mock; it speaks the same protocol.

Same for KMS via LocalStack: the envelope-encryption code path is exercised in development rather than first tried in production, which is where a crypto path should never be first tried.

**v1 needs none of this except Postgres.** Local disk through `storage.ts` is fine until there is something to publish to strangers. Add MinIO when S3 arrives, LocalStack when integration credentials do. The Compose file grows with the versions.

## What v1 actually stands up

**Docker Compose and a dev server. No AWS account.**

v1 is single-user with local Postgres, no accounts, no publishing to strangers, no personalization, no integrations, no 3D. Its verification list asks you to open the published URL in an incognito window, which a dev server satisfies completely.

Everything in this document lands with **v3** — the release that has real users, which is the same boundary every other v3 control sits on ([../security/README.md](../security/README.md)).

The temptation to build the infrastructure first should be resisted specifically because it feels productive. The long pole in this project is the renderer and whether it produces something genuinely beautiful ([../v1/spec.md](../v1/spec.md), Risk 1). A perfect VPC does not move that risk at all.
