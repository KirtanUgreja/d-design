# Build Pipeline

The stack gained a build pipeline with production credentials, and that pipeline is now a path into everything. This is OWASP **A03:2025 Software Supply Chain Failures** applied to the half you own rather than the half you install.

The asymmetry worth internalizing: **a compromise here skips every control in this directory.** Prompt injection defenses, RLS, the sandbox, the fetch worker's isolation — all of them assume the code running in production is the code you wrote. CI is where that assumption is made.

## GitHub Actions OIDC to AWS

Choosing OIDC over long-lived keys ([../techstack/infrastructure.md](../techstack/infrastructure.md)) was right and removes the credential class that most cloud breaches start with. It replaces it with a **trust policy**, which is a smaller surface that fails in less obvious ways.

### The two ways this is gotten wrong

**Missing `sub` condition entirely.** Datadog Security Labs found real cases of this in the wild. The consequence is not "any repo in your org" — it is **any GitHub Actions workflow on the planet can assume the role.** Anyone who can push a workflow file to any public repository has your AWS credentials.

**A wildcard `sub`.** `repo:your-org/*` means every repository under the organization: test projects, proof-of-concepts, a repo created by anyone with permission to create repos. Wildcards in trust policies remain among the most exploited misconfigurations at the post-exploitation stage — an attacker who gets a foothold in *any* org repo pivots straight to production infrastructure.

### The rules

```jsonc
// scope to repo AND ref AND environment — not one of the three
"StringEquals": {
  "token.actions.githubusercontent.com:sub":
    "repo:<org>/<repo>:environment:production"
}
```

- **Never `StringLike` with a wildcard** on `sub`. `StringEquals` on an exact value.
- **Production deploys go through a GitHub Environment** with required reviewers, and the trust policy conditions on `environment:production`. That makes the approval gate part of the credential, not a UI preference.
- **One role per repo per purpose.** The fetch-worker repo's role can push to its ECR repository and update its own service. It has no reason to reach RDS, KMS, or the app's resources, and the two-repo split is only a security boundary if the credentials respect it.
- **Terraform gets its own role**, and `plan` on a pull request runs read-only. `apply` runs only from `main`, from the production environment.

### The July 2026 subject-claim change — this applies directly

**On 15 July 2026 GitHub began issuing OIDC tokens with a new `sub` format for newly created repositories**, embedding numeric organization and repository IDs instead of names.

Both repositories in this project are yet to be created, so **they will use the new format**, and a trust policy copied from any tutorial written before mid-2026 will either not match or — worse — be written loosely to make it match.

The immutable-ID format is better: renaming a repo, or deleting one and recreating it with the same name, no longer silently transfers trust. Write the policy against the new format deliberately rather than fighting it.

## Terraform state is a secret

The state file contains resource attributes, and resource attributes include database endpoints, connection details, and in many cases generated secrets in plaintext. **The exposure of an over-broad CI role is measured in every secret that role can read, for as long as the policy stays open** — and state is the densest concentration of them.

| | |
|---|---|
| **S3 backend, encrypted, versioned, public access blocked** | Bucket policy denies everything except the two Terraform roles |
| **State bucket is not the assets bucket** | Separate bucket, separate policy, no shared blast radius |
| **Locking on** | Concurrent applies corrupt state, and a corrupted state is an outage you fix by hand |
| **Prefer generated-at-use over stored** | Where a secret can live in Secrets Manager and be referenced rather than created by Terraform, do that — it keeps the value out of state entirely |

## Workflow security

**Never `pull_request_target` with a checkout of the PR head.** That combination runs untrusted code with access to secrets, and it is the standard "pwn request" pattern. Untrusted contributions run on `pull_request`, which has no secrets.

Solo, this looks like a non-issue. It becomes one the moment the repo has a second contributor or goes public, and the mistake is much cheaper to not make than to find.

- **Pin third-party actions to a commit SHA**, not a tag. A tag is mutable, and a compromised action runs with your OIDC token.
- **`permissions:` declared explicitly at the top of every workflow**, defaulting to `contents: read`. `id-token: write` only where OIDC is actually used.
- **Nothing untrusted reaches a shell.** Branch names and PR titles are attacker-controlled and end up in `run:` blocks through interpolation. Use `env:` and quote.

## Publishing `@d-design/schema`

The moment you publish, you are a link in a supply chain — even when the only consumer is your own fetch worker.

- **npm trusted publishing (OIDC)**, so there is no long-lived npm token to steal ([../coderules/typescript.md](../coderules/typescript.md)).
- **Provenance attestations are not generated for private repositories**, and this repo is private. Trusted publishing still removes the token; the Sigstore attestation does not appear. Acceptable, and worth knowing so nobody assumes a verification step that does not exist.
- **Publish only from `main`, through the environment gate.** A package published from a branch is a package nobody reviewed.

## Container images

The fetch worker's image contains headless Chromium and every hostile-input parser in the project ([infrastructure.md](infrastructure.md)). It is the highest-value image and the one most likely to carry a known CVE.

- **ECR scan-on-push**, and a critical finding fails the deploy
- **Rebuild on a schedule, not only on code change.** The base image accumulates CVEs while your code is stable, and a service that has not deployed in six weeks is running six weeks of unpatched Chromium
- **Pin the base image by digest.** A moving tag is a supply-chain input you did not review
- **Non-root, read-only root filesystem, no shell** where practical

## What this adds to the release gate

Additions to [operations.md](operations.md):

- No OIDC trust policy uses a wildcard or omits `sub`
- Production deploys are conditioned on a GitHub Environment with a reviewer
- Terraform state bucket blocks public access, is encrypted and versioned, and is readable only by the Terraform roles
- No workflow combines `pull_request_target` with a PR-head checkout
- Third-party actions are SHA-pinned; every workflow declares `permissions`
- ECR scan-on-push is enabled and critical findings block the deploy
- The fetch worker image has been rebuilt within the current patch window
