"""Write the seeded art directions to the fixture both languages read.

    uv run python -m scripts.export_art_directions

The fixture is checked in, not generated at test time, and that is the point:
`api/tests/test_art_direction_seed.py` fails if `seed.py`'s output differs from
the file, and `web`'s `art-direction.test.ts` reads the same file and asserts
that the record renders to the same CSS variables as the v1 TypeScript
constant. A fixture regenerated inside the test would agree with itself.

Same arrangement as `schema/fixtures/*.json` — one file, a test on each side —
and the same arrangement `test_visual_seed.py` uses for the FNV-1a table. It is
this repository's answer to a cross-language invariant, and this is the second
place it has been needed.

The payload and the path are `features/art_direction/seed.py`'s, not this
file's. A script is a way to run something, never the place it is defined.
"""

import json
import sys

from features.art_direction.seed import FIXTURE, wire_payload

if __name__ == "__main__":
    FIXTURE.write_text(json.dumps(wire_payload(), indent=2, sort_keys=True) + "\n")
    sys.stdout.write(f"art directions: wrote {FIXTURE.name}\n")
