"""The calibration report must count absence, never read it as agreement.

A hand that is not gripping carries an empty `flexionAxis`, which is absence
of measurement. The instrument that closed the thumb calibration counts those
hands separately, because a report that silently dropped them would present
34 measured hands as if they were the whole 66-hand batch, and "silence is
not a pass" is this lane's oldest rule.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR / "scripts"))

from report_axis_calibration import collect  # noqa: E402


def receipt(movement, phases):
    return {"movementId": movement, "phases": phases}


def hand(report):
    return {"flexionAxis": report}


THUMB = {
    "namedAxis": 2,
    "turnedDegrees": [33.363, 6.042, -19.977],
    "namedAxisShare": 0.5988,
    "dominantAxis": 0,
    "dominanceMarginDegrees": 13.386,
    "measured": True,
    "asserted": False,
}


class CollectTest(unittest.TestCase):
    def test_an_empty_hand_is_counted_as_absence_not_as_a_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "a.render.json").write_text(
                json.dumps(
                    receipt(
                        "drill_a",
                        [
                            {
                                "name": "contact",
                                "hands": {
                                    "l": hand({}),
                                    "r": hand({"thumb": THUMB}),
                                },
                            }
                        ],
                    )
                ),
                encoding="utf-8",
            )

            readings, covered, empty = collect(directory)

        self.assertEqual(1, len(readings))
        self.assertEqual(1, covered)
        self.assertEqual(1, empty, "an empty report is absence and is counted")
        self.assertEqual("thumb", readings[0]["digit"])
        # `largest` is the magnitude the floor judges: the biggest absolute
        # component, not the named one and not a sum.
        self.assertAlmostEqual(33.363, readings[0]["largest"], places=6)

    def test_a_missing_hands_block_does_not_crash_or_invent_a_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / "b.render.json").write_text(
                json.dumps(receipt("drill_b", [{"name": "ready"}])),
                encoding="utf-8",
            )

            readings, covered, empty = collect(directory)

        self.assertEqual([], readings)
        self.assertEqual(0, covered)
        self.assertEqual(2, empty, "both hands of the phase are unmeasured")


if __name__ == "__main__":
    unittest.main()
