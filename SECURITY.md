# Security policy

d-design runs model-written HTML and holds model keys, so security reports matter to us.

**Please report a vulnerability privately** through GitHub: the repository's **Security** tab → **Report a vulnerability**. Do not open a public issue.

Include what you found, how to reproduce it and what an attacker could do with it. We aim to reply within 7 days.

In scope: escaping the slide sanitizer or the CSP of an exported deck, reading or changing another user's decks, getting past the sign-up allowlist or the spend cap, and leaking the model key.

The threat model and every control are in [`docs/security/`](docs/security/README.md).
