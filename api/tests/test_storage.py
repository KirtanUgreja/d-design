"""storage.py against MinIO over the real S3 API. Not a mock — the same
protocol, which is what stops the "second implementation" from ever needing to
exist."""

from lib.ids import new_id
from lib.result import Err, Ok
from lib.storage import get_object, put_object


async def test_object_round_trips() -> None:
    key = f"phase-00/{new_id()}.txt"
    await put_object(key, b"hello from phase 00", "text/plain")

    got = await get_object(key)
    assert isinstance(got, Ok)
    assert got.value == b"hello from phase 00"


async def test_missing_key_is_a_result_not_an_exception() -> None:
    got = await get_object(f"phase-00/{new_id()}-absent")
    assert isinstance(got, Err)
    assert got.error.code == "not_found"
