"""Write the seeded motion vocabularies to the fixture both languages read.

    uv run python -m scripts.export_motion

Checked in rather than generated at test time, for the reason
`scripts/export_art_directions.py` spells out: a fixture built by the code under
test agrees with itself. `api/tests/test_motion_seed.py` fails when this module
and the file disagree, and `art-direction.test.ts` asserts the same records
still produce v1's vocabularies.

The payload and the path are `features/motion/seed.py`'s. A script is a way to
run something, never the place it is defined.
"""

import json
import sys

from features.motion.seed import FIXTURE, wire_payload

if __name__ == "__main__":
    FIXTURE.write_text(json.dumps(wire_payload(), indent=2, sort_keys=True) + "\n")
    sys.stdout.write(f"motion: wrote {FIXTURE.name}\n")
