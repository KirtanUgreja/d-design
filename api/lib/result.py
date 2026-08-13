"""Result: the tagged pair for expected failures.

python.md: expected failures return a Result; only bugs raise. This is the
Python spelling of the TypeScript Result in lib/result.ts, and mypy --strict
makes the match exhaustive so a caller that forgets a branch fails the gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True)
class Ok[T]:
    value: T


@dataclass(frozen=True)
class Err[E]:
    error: E


Result = Ok[T] | Err[E]


def ok[T](value: T) -> Ok[T]:
    return Ok(value)


def err[E](error: E) -> Err[E]:
    return Err(error)
