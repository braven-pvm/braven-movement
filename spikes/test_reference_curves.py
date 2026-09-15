"""The contract for the shape of `reference-curves.json`.

WHY THESE EXIST. The export widened on 1 September: a curve became a mapping of
a unit and its values instead of a bare list. `video_dry_run.py` was widened
with it; `video_elbow_curve.py` and `video_phase_align.py` were not, and both
kept iterating the curve, which now yields the KEYS. Every suite stayed green
for six days, because each of those readers was tested against a MOCK that had
also not been widened. A mock that has drifted from its producer tests nothing
but itself.

So the last test in this file reads the REAL exported artefact when it is
present. It is the only test here that can catch the next widening.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import numpy as np

from reference_curves import SCHEMA_VERSION, curve_length, curve_values

OUTPUT = Path(__file__).resolve().parent / "poc-output" / "video"
EXPORTED = OUTPUT / "reference-curves.json"


def file_at(version) -> dict:
    return {"schemaVersion": version}


DRILL = {"curves": {"c": {"unit": "degrees", "values": [1.0, None, 3.0]}}}


class CurveValuesReadsTheDeclaredShape(unittest.TestCase):

    def test_it_returns_the_values_as_floats_and_drops_the_gaps(self):
        found = curve_values(file_at(SCHEMA_VERSION), DRILL, "c", "degrees")

        self.assertEqual(list(found), [1.0, 3.0])
        self.assertEqual(found.dtype, np.dtype(float))

    def test_another_schema_version_refuses(self):
        for version in (SCHEMA_VERSION - 1, SCHEMA_VERSION + 1, None):
            with self.subTest(version=version):
                with self.assertRaises(SystemExit):
                    curve_values(file_at(version), DRILL, "c", "degrees")

    def test_the_version_one_bare_list_refuses_rather_than_being_read(self):
        """THE EXACT SHAPE THAT BROKE TWO READERS. A reader that accepts both
        shapes cannot tell a unit from a measurement, and removing that
        assumption is the whole reason the export widened."""
        with self.assertRaises(SystemExit):
            curve_values(file_at(SCHEMA_VERSION),
                         {"curves": {"c": [1.0, 2.0]}}, "c", "degrees")

    def test_a_curve_in_another_unit_refuses(self):
        """`footHeightGapCm` is centimetres in a file of angles. Asking for
        degrees and being given centimetres must stop, not scale."""
        with self.assertRaises(SystemExit):
            curve_values(file_at(SCHEMA_VERSION), DRILL, "c", "centimetres")

    def test_a_curve_that_is_not_there_refuses(self):
        with self.assertRaises(SystemExit):
            curve_values(file_at(SCHEMA_VERSION), DRILL, "absent", "degrees")


class CurveLengthCountsValuesAndNeverKeys(unittest.TestCase):
    """`rank_against_library` skipped a curve shorter than two points. The
    two-key mapping has length two, so it PASSED that guard and carried the
    words 'unit' and 'values' into the ranking that guards the whole method."""

    def test_it_counts_the_values(self):
        self.assertEqual(curve_length(file_at(SCHEMA_VERSION), DRILL, "c"), 2)

    def test_a_bare_list_counts_as_nothing_rather_than_as_its_keys(self):
        found = curve_length(file_at(SCHEMA_VERSION),
                             {"curves": {"c": [1.0, 2.0]}}, "c")

        self.assertEqual(found, 0)

    def test_a_one_value_curve_is_below_the_bar_a_two_key_mapping_passed(self):
        one = {"curves": {"c": {"unit": "degrees", "values": [7.0]}}}

        self.assertEqual(curve_length(file_at(SCHEMA_VERSION), one, "c"), 1)

    def test_a_missing_curve_counts_as_nothing(self):
        self.assertEqual(
            curve_length(file_at(SCHEMA_VERSION), DRILL, "absent"), 0)

    def test_another_schema_version_refuses(self):
        with self.assertRaises(SystemExit):
            curve_length(file_at(SCHEMA_VERSION + 1), DRILL, "c")


class TheExportedFileMatchesTheContract(unittest.TestCase):
    """THE ONLY TEST HERE THAT CAN CATCH THE NEXT WIDENING. Everything above
    is a mock, and a mock is what let the last widening pass unseen."""

    def setUp(self):
        if not EXPORTED.exists():
            self.skipTest("reference-curves.json is not exported here")
        self.file = json.loads(EXPORTED.read_text(encoding="utf-8"))

    def test_the_exported_file_declares_the_version_this_reader_expects(self):
        self.assertEqual(self.file["schemaVersion"], SCHEMA_VERSION)

    def test_every_curve_of_every_movement_is_readable_in_its_own_unit(self):
        for name, drill in self.file["movements"].items():
            for measure, curve in drill["curves"].items():
                with self.subTest(movement=name, measure=measure):
                    found = curve_values(self.file, drill, measure,
                                         curve["unit"])

                    self.assertEqual(found.dtype, np.dtype(float))
                    self.assertEqual(
                        len(found),
                        len([v for v in curve["values"] if v is not None]))

    def test_the_elbow_curve_the_two_consumers_read_is_in_degrees(self):
        """Both consumers ask for this measure in degrees by name. If the
        export ever changes its unit, they must stop rather than convert."""
        for name, drill in self.file["movements"].items():
            with self.subTest(movement=name):
                self.assertEqual(
                    drill["curves"]["leftElbowFlexionDegrees"]["unit"],
                    "degrees")


if __name__ == "__main__":
    unittest.main()
