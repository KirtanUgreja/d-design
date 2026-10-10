"""The JWT check (phase 29 -> A3/A4): only a fresh EdDSA token signed by
Better Auth's key, for our audience and issuer, names a caller. Everything
else, an unreachable JWKS included, is refused."""

from __future__ import annotations

import json
import time

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jwt import PyJWK
from jwt.algorithms import OKPAlgorithm

from auth import AUDIENCE, Caller, Verifier
from lib.result import Err, Ok

ISSUER = "http://localhost:3000"
KEY = Ed25519PrivateKey.generate()
OTHER = Ed25519PrivateKey.generate()
PUBLIC = PyJWK(json.loads(OKPAlgorithm.to_jwk(KEY.public_key())), algorithm="EdDSA")


def _token(key: object = KEY, alg: str = "EdDSA", **claims: object) -> str:
    now = int(time.time())
    body = {
        "sub": "user-1",
        "email": "a@b.co",
        "name": "A",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + 300,
    } | claims
    return jwt.encode({k: v for k, v in body.items() if v is not None}, key, algorithm=alg)  # type: ignore[arg-type]


VERIFIER = Verifier(lambda _: PUBLIC, issuer=ISSUER)


def test_a_good_token_names_its_caller() -> None:
    got = VERIFIER.verify(f"Bearer {_token()}")
    assert isinstance(got, Ok)
    assert got.value == Caller("user-1", "a@b.co", "A")


def test_every_bad_token_is_refused() -> None:
    now = int(time.time())
    bad = [
        None,
        "",
        "Basic abc",
        "Bearer ",
        "Bearer not-a-jwt",
        f"Bearer {_token(OTHER)}",  # signed by someone else
        f"Bearer {_token(aud='another-api')}",
        f"Bearer {_token(iss='https://evil.example')}",
        f"Bearer {_token(exp=now - 10)}",
        f"Bearer {_token(sub=None)}",
        f"Bearer {_token(exp=None)}",
        f"Bearer {_token(key='secret-secret-secret-secret-1234', alg='HS256')}",  # alg swap
    ]
    for header in bad:
        assert isinstance(VERIFIER.verify(header), Err), header


def test_an_unreachable_jwks_refuses() -> None:
    def down(_: str) -> PyJWK:
        raise ConnectionError("jwks unreachable")

    assert isinstance(Verifier(down, issuer=ISSUER).verify(f"Bearer {_token()}"), Err)
