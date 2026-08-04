"""The base every schema model inherits.

Two decisions that hold for every model in this package, both about what
crosses the language boundary rather than about Python itself.

**Wire names are camelCase, Python names are snake_case.** `docs/coderules/
structure.md` says camelCase in TypeScript, snake_case in Python, for
functions and variables — "the rules are parallel, the spellings are native."
Applied to the codegen boundary: `Experience.brand_id` in Python is `brandId`
in the JSON Schema, and therefore `brandId` in the generated Zod validator and
inferred type, which is what `docs/v1/scene-schema.md` actually specifies
(`brandId`, `artDirection`, `createdAt`, ...). Without the alias, the wire
shape would be Python's naming convention leaking across the boundary — a
transliteration, which the same doc names as the mistake to avoid.
`populate_by_name=True` keeps `Model(brand_id=...)` working in Python code, and
`model_json_schema()`'s `by_alias=True` default is what makes the alias the one
that actually ships.

**`extra="forbid"`.** Pydantic's default is to ignore an unknown key; Zod's
`z.object` strips one. Both "succeed", so a field neither side knows about
would be accepted quietly in both languages — and the generated JSON Schema is
where the two would silently agree to be permissive if one of them were
stricter than the other. Forbidding puts `additionalProperties: false` in the
schema, which the emitter turns into `z.strictObject`, and now both validators
return the same verdict on the same input — the property the cross-language
fixture test asserts (docs/coderules/python.md -> "Test"). It is also right on
its own terms: model output is untrusted input, and an unknown field is a
signal, not noise.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Schema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )
