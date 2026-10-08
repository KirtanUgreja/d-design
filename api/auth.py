"""Who is calling: Better Auth's JWT, verified (docs/v4/plan/29-accounts-deploy.md).

The web app signs a short-lived EdDSA token per proxied request; this checks
its signature against Better Auth's JWKS, its issuer, audience, expiry and
algorithm. Anything that grants fails closed (AGENTS.md rule 10): every
failure, an unreachable JWKS included, is "not signed in". Python never reads
Better Auth's tables; the token is the only contract.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import jwt
from jwt import PyJWK, PyJWKClient

from lib.result import Result, err, ok

ALGORITHMS = ["EdDSA"]  # the JWT plugin's default; nothing else is accepted
AUDIENCE = "d-design-api"


@dataclass(frozen=True)
class Caller:
    id: str  # Better Auth's user id, the token's sub
    email: str
    name: str


KeyFor = Callable[[str], PyJWK]  # a token -> the JWKS key that signed it


@dataclass(frozen=True)
class Verifier:
    key_for: KeyFor
    issuer: str
    audience: str = AUDIENCE

    @staticmethod
    def remote(base_url: str) -> Verifier:
        """Keys from ``<base_url>/api/auth/jwks``, cached for five minutes."""
        client = PyJWKClient(f"{base_url}/api/auth/jwks", lifespan=300, timeout=5)
        return Verifier(client.get_signing_key_from_jwt, issuer=base_url)

    def verify(self, header: str | None) -> Result[Caller, str]:
        if not header or not header.startswith("Bearer "):
            return err("no token")
        token = header.removeprefix("Bearer ").strip()
        try:
            key = self.key_for(token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=ALGORITHMS,
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            )
        # Fails closed on anything at all: a bad token, a key we can't fetch, a
        # library surprise. Refusing is always safe here; granting never is.
        except Exception as e:
            return err(type(e).__name__)
        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub:
            return err("no subject")
        email, name = claims.get("email"), claims.get("name")
        return ok(
            Caller(
                sub,
                email if isinstance(email, str) else "",
                name if isinstance(name, str) else "",
            )
        )
