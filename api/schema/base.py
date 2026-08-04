"""The base every schema model inherits.

`extra="forbid"` is not a style preference. Pydantic's default is to ignore an
unknown key; Zod's `z.object` strips one. Both "succeed", so a model that sends
a field neither side knows about would be accepted quietly in both languages —
and the generated JSON Schema is where the two would silently disagree if one
of them were stricter than the other.

Forbidding puts `additionalProperties: false` in the JSON Schema, which the
emitter turns into `z.strictObject`, which makes the two validators return the
same verdict on the same input. That agreement is the property the
cross-language fixture test asserts (docs/coderules/python.md -> "Test").

It is also the right behaviour on its own terms: model output is untrusted
input, and a field the schema does not know about is a signal, not noise.
"""

from pydantic import BaseModel, ConfigDict


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid")
