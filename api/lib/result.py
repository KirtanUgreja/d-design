"""The one error type.

Expected failures return a `Result`; bugs raise. The line is one question:
*would a correct system ever produce this?* If yes, `Result`. If no, raise.

`mypy --strict` is what makes this worth having — it forces a caller to handle
both branches, so the permissive one can never be implicit. Without a strict
checker `Result` in Python is ceremony.

docs/coderules/python.md -> "Errors", docs/coderules/patterns.md -> rule 5
"""

from dataclasses import dataclass
from typing import Literal, NoReturn

# The codes that exist. A literal union rather than free strings, so a caller
# matching on one cannot typo a branch that then silently never runs.
ErrorCode = Literal[
    "unauthorized",
    "not_found",
    "invalid_input",
    "quota_exceeded",
    "upstream_unavailable",
    "repair_exhausted",
]


@dataclass(frozen=True, slots=True)
class AppError:
    code: ErrorCode
    message: str


@dataclass(frozen=True, slots=True)
class Ok[T]:
    value: T


@dataclass(frozen=True, slots=True)
class Err[E]:
    error: E


type Result[T, E = AppError] = Ok[T] | Err[E]


def ok[T](value: T) -> Ok[T]:
    return Ok(value)


def err(code: ErrorCode, message: str = "") -> Err[AppError]:
    return Err(AppError(code, message))


def unreachable(value: NoReturn) -> NoReturn:
    """Exhaustiveness marker for `match` over a Result.

    A branch this is called from is one mypy has proved cannot happen. Reaching
    it at runtime means the type was lied to, which is a bug, so it raises.
    """
    raise AssertionError(f"unreachable: {value!r}")
