"""The shape of `reference-curves.json`, owned in one place.

WHY THIS MODULE EXISTS. On 2026-09-01 the export widened: a curve stopped being
a bare list of numbers and became `{"unit": ..., "values": [...]}`, so that
`footHeightGapCm` could declare centimetres in a file that announces itself as
angles. `video_dry_run.py` was widened with it. **Two other readers were not,
and both kept iterating the curve, which now yields the KEYS.** One of them
collected the strings `"unit"` and `"values"` and passed a length guard with
them. Nothing said so for six days, because no test ran either reader against
the real file: `test_video_phase_align.py` builds its reference as a bare list,
which is the shape the export no longer writes.

So the contract lives here, with no heavy imports, and everything depends on
it: `export_reference_curves.py` takes its version number from here, and every
consumer reads through `curve_values` rather than subscripting the file. One
definition means one mutation can fail every reader at once.

THE READER REFUSES RATHER THAN COPES. It does not accept the old bare list as
well. A reader that accepts both shapes cannot tell a unit from a measurement,
and the whole point of the widening was to stop a unit being assumed.
"""

from __future__ import annotations

import numpy as np

SCHEMA_VERSION = 2


def curve_values(reference: dict, drill: dict, name: str,
                 unit: str) -> np.ndarray:
    """One curve, as floats, with its schema version and its unit checked.

    `reference` is the whole file, which carries the version. `drill` is one
    movement out of `reference["movements"]`. Gaps, written as null, are
    dropped: a curve is not required to be complete.
    """
    found = reference.get("schemaVersion")
    if found != SCHEMA_VERSION:
        raise SystemExit(
            f"reference-curves.json is schema version {found!r}, and this "
            f"reader was written for {SCHEMA_VERSION}. Read the file before "
            "changing the number: at version 2 each curve became a mapping of "
            "a unit and its values, and every reader that assumed a bare list "
            "silently built an array of the words 'unit' and 'values'.")
    curve = drill.get("curves", {}).get(name)
    if curve is None:
        raise SystemExit(f"no curve named {name!r} in this movement")
    if not isinstance(curve, dict) or "values" not in curve:
        raise SystemExit(
            f"curve {name!r} is not a mapping of a unit and its values. This "
            "is the version-1 shape, and reading it as a list of numbers is "
            "the exact fault this module exists to stop.")
    if curve.get("unit") != unit:
        raise SystemExit(
            f"curve {name!r} is in {curve.get('unit')!r}, not {unit!r}. A "
            "curve's unit is declared, never assumed.")
    return np.array([v for v in curve["values"] if v is not None], dtype=float)


def curve_length(reference: dict, drill: dict, name: str) -> int:
    """How many values a curve has, WITHOUT requiring a unit.

    A ranking across every movement compares one measure to itself, so it does
    not care what the unit is; it only needs to skip a curve too short to warp.
    It still may not iterate the mapping, which is what made a two-key
    dictionary pass a `len(curve) < 2` guard.
    """
    found = reference.get("schemaVersion")
    if found != SCHEMA_VERSION:
        raise SystemExit(
            f"reference-curves.json is schema version {found!r}, not "
            f"{SCHEMA_VERSION}")
    curve = drill.get("curves", {}).get(name)
    if not isinstance(curve, dict) or "values" not in curve:
        return 0
    return len([v for v in curve["values"] if v is not None])
