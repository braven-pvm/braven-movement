"""The hand-orientation measures do what their definitions say. Report-only.

Two layers. The pure layer holds each measure to its written convention with
worked examples and decoys that can actually fail: a thumbs-up hand must read
0 and a thumbs-down hand 180, so a reversed ray, a swapped axis or a collapsed
convention cannot pass. The solver layer calls the measures on a real solved
drill, the chest catch of Erin's "Thumbs shouldn't be up" note, and holds the
receipt rows to the report-only contract: band null, verdict "reported",
grading untouched.

What the solver layer deliberately does NOT assert: left/right thumb symmetry.
On the current build the two thumbs read about 20 degrees apart at every
contact because spread_fingers anti-mirrors the thumb posture (the rig mirrors
on same-signed parameters; the code negates). That asymmetry is a finding this
instrument exists to expose, not a bound to hide it under.
"""

from __future__ import annotations

import unittest

from hand_orientation import (
    CONVENTIONS,
    REPORTED,
    WORLD_UP,
    finger_up_degrees,
    measure_hand,
    receipt_rows,
    receipt_section,
    thumb_to_ball_degrees,
    thumb_up_degrees,
)
from hand_orientation_crosscheck import _atan2_degrees, recompute
from segment_measures import SegmentMeasureError

# Only a genuinely absent solver may skip. Catching every exception here would
# swallow a break in the code under test and skip the guard in silence.
try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False

if SOLVER:
    # Deliberately unguarded: a failure here is a real break and must be loud.
    from movement_definition import load as load_definition
    from movement_engine import (
        WORLD_UP as ENGINE_WORLD_UP,
        definition_path,
        load_character,
    )
    from possession_solve import solve_movement

# The drill of Erin's chest-catch note, and the phase her cue is about.
DRILL = "netball_two_hand_catch_chest"


class TheConventionsHold(unittest.TestCase):
    """Each measure against its own written definition, endpoints first."""

    def test_a_thumb_pointing_straight_up_reads_zero(self) -> None:
        self.assertAlmostEqual(
            thumb_up_degrees(thumb_base=(0, 100, 0), thumb_tip=(0, 107, 0)),
            0.0,
            places=6,
        )

    def test_a_level_thumb_reads_ninety(self) -> None:
        self.assertAlmostEqual(
            thumb_up_degrees(thumb_base=(0, 100, 0), thumb_tip=(7, 100, 0)),
            90.0,
            places=6,
        )

    def test_a_thumb_pointing_straight_down_reads_one_eighty(self) -> None:
        """The decoy that catches a reversed ray or a collapsed convention.

        A measure that reads the ray tip-to-base reports this thumb as up,
        and a measure that lost its range reports it as 0 or 90. Both fail
        here, where the code can reach them.
        """
        self.assertAlmostEqual(
            thumb_up_degrees(thumb_base=(0, 107, 0), thumb_tip=(0, 100, 0)),
            180.0,
            places=6,
        )

    def test_the_thumb_worked_example(self) -> None:
        """The docstring's own numbers: ray (3, 4, 0) reads 36.87."""
        self.assertAlmostEqual(
            thumb_up_degrees(thumb_base=(0, 100, 0), thumb_tip=(3, 104, 0)),
            36.8698976,
            places=5,
        )

    def test_fingers_up_level_and_down(self) -> None:
        wrist = (0, 90, 10)
        for knuckle, expected in (
            ((0, 98, 10), 0.0),
            ((8, 90, 10), 90.0),
            ((0, 82, 10), 180.0),
        ):
            self.assertAlmostEqual(
                finger_up_degrees(wrist=wrist, middle_knuckle=knuckle),
                expected,
                places=6,
            )

    def test_the_finger_worked_example(self) -> None:
        """Ray (0, 4, -3) reads 36.87, off the vertical toward her front."""
        self.assertAlmostEqual(
            finger_up_degrees(wrist=(0, 90, 10), middle_knuckle=(0, 94, 7)),
            36.8698976,
            places=5,
        )

    def test_a_thumb_at_the_balls_middle_reads_zero(self) -> None:
        self.assertAlmostEqual(
            thumb_to_ball_degrees(
                thumb_base=(10, 100, 0),
                thumb_tip=(14, 100, 0),
                ball_centre=(30, 100, 0),
            ),
            0.0,
            places=6,
        )

    def test_a_thumb_along_the_surface_reads_ninety(self) -> None:
        self.assertAlmostEqual(
            thumb_to_ball_degrees(
                thumb_base=(10, 100, 0),
                thumb_tip=(10, 107, 0),
                ball_centre=(30, 100, 0),
            ),
            90.0,
            places=6,
        )

    def test_a_thumb_pointing_away_reads_one_eighty(self) -> None:
        self.assertAlmostEqual(
            thumb_to_ball_degrees(
                thumb_base=(10, 100, 0),
                thumb_tip=(6, 100, 0),
                ball_centre=(30, 100, 0),
            ),
            180.0,
            places=6,
        )

    def test_the_ball_worked_example(self) -> None:
        """Ray (3, 4, 0) against to-centre (10, 0, 0) reads 53.13."""
        self.assertAlmostEqual(
            thumb_to_ball_degrees(
                thumb_base=(10, 100, 0),
                thumb_tip=(13, 104, 0),
                ball_centre=(20, 100, 0),
            ),
            53.1301024,
            places=5,
        )

    def test_the_measures_are_side_agnostic(self) -> None:
        """Mirroring a hand across X leaves every up-angle unchanged.

        Up is Y, so an X-mirror moves nothing off the up cone, and the ball
        measure mirrors with the ball. A side special-case, the fault class
        grip.py documents for palm normals, would break this.
        """
        base, tip, centre = (10, 100, 5), (13, 104, 3), (25, 95, 0)
        mirror = lambda p: (-p[0], p[1], p[2])  # noqa: E731
        self.assertAlmostEqual(
            thumb_up_degrees(thumb_base=base, thumb_tip=tip),
            thumb_up_degrees(thumb_base=mirror(base), thumb_tip=mirror(tip)),
            places=9,
        )
        self.assertAlmostEqual(
            thumb_to_ball_degrees(
                thumb_base=base, thumb_tip=tip, ball_centre=centre
            ),
            thumb_to_ball_degrees(
                thumb_base=mirror(base),
                thumb_tip=mirror(tip),
                ball_centre=mirror(centre),
            ),
            places=9,
        )

    def test_a_zero_length_thumb_is_an_error_not_a_number(self) -> None:
        with self.assertRaises(SegmentMeasureError):
            thumb_up_degrees(thumb_base=(1, 2, 3), thumb_tip=(1, 2, 3))


class TheTwoFormulationsAgree(unittest.TestCase):
    """The primary acos read and the crosscheck's atan2 read, on the same
    exact vectors, must agree to numerical precision. A clamp bug or a
    normalisation bug in either shows up here without a solve."""

    def test_across_a_spread_of_directions(self) -> None:
        rays = [
            (0.0, 1.0, 0.0),
            (0.0, -1.0, 0.0),
            (1.0, 0.0, 0.0),
            (3.0, 4.0, 0.0),
            (1e-3, 1.0, 0.0),  # near parallel, where acos loses precision
            (-1e-3, -1.0, 0.0),  # near opposite
            (2.0, -5.0, 7.0),
        ]
        from hand_orientation import thumb_up_degrees as primary

        for ray in rays:
            with self.subTest(ray=ray):
                self.assertAlmostEqual(
                    primary(thumb_base=(0, 0, 0), thumb_tip=ray),
                    _atan2_degrees(ray, WORLD_UP),
                    places=6,
                )

    def test_through_the_crosscheck_row_reader(self) -> None:
        """recompute() on unrounded joints equals the primary measure."""
        joints = {
            "l_thumb1": (10.0, 100.0, 5.0),
            "l_thumb3": (13.0, 104.0, 3.0),
            "l_wrist": (8.0, 95.0, 6.0),
            "l_middle1": (9.0, 102.0, 4.0),
        }
        ball = (25.0, 95.0, 0.0)
        measured = measure_hand(
            list(joints.values()),
            {name: number for number, name in enumerate(joints)},
            "l",
            ball,
        )
        for suffix in CONVENTIONS:
            value, budget = recompute(joints, ball, f"left{suffix}")
            with self.subTest(measure=suffix):
                self.assertAlmostEqual(value, measured[suffix], places=6)
                self.assertGreater(budget, 0.0)


class TheReceiptRowsAreReportOnly(unittest.TestCase):
    """The row contract, without a solver: shaped like coaching rows, banded
    by nothing, and self-describing."""

    JOINTS = {
        "l_thumb1": (10.0, 100.0, 5.0),
        "l_thumb3": (13.0, 104.0, 3.0),
        "l_wrist": (8.0, 95.0, 6.0),
        "l_middle1": (9.0, 102.0, 4.0),
        "r_thumb1": (-10.0, 100.0, 5.0),
        "r_thumb3": (-13.0, 104.0, 3.0),
        "r_wrist": (-8.0, 95.0, 6.0),
        "r_middle1": (-9.0, 102.0, 4.0),
    }

    def rows(self) -> list[dict]:
        index = {name: number for number, name in enumerate(self.JOINTS)}
        points = list(self.JOINTS.values())
        return receipt_rows(points, index, (0.0, 95.0, -20.0))

    def test_six_rows_left_before_right(self) -> None:
        names = [row["measure"] for row in self.rows()]
        self.assertEqual(
            names,
            [
                "leftThumbUpDegrees",
                "leftFingerUpDegrees",
                "leftThumbToBallDegrees",
                "rightThumbUpDegrees",
                "rightFingerUpDegrees",
                "rightThumbToBallDegrees",
            ],
        )

    def test_no_row_carries_a_band_or_a_grading_verdict(self) -> None:
        for row in self.rows():
            with self.subTest(measure=row["measure"]):
                self.assertIsNone(row["band"])
                self.assertEqual(row["verdict"], REPORTED)
                self.assertNotIn(row["verdict"], ("below", "within", "above"))

    def test_every_row_explains_its_own_zero(self) -> None:
        """The cue slot carries the convention, so a receipt reads alone."""
        for row in self.rows():
            with self.subTest(measure=row["measure"]):
                self.assertIn("0 is", row["cue"])


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class TheMeasuresReadASolvedDrill(unittest.TestCase):
    """The chest catch, solved for real. Slow, and the only place the measures
    meet the pose Erin actually graded."""

    @classmethod
    def setUpClass(cls) -> None:
        character = load_character()
        cls.result = solve_movement(character, DRILL)
        cls.definition = load_definition(definition_path(DRILL))
        cls.section = receipt_section(cls.result, cls.definition)

    def test_the_two_up_constants_are_the_same_up(self) -> None:
        self.assertEqual(tuple(WORLD_UP), tuple(ENGINE_WORLD_UP))

    def test_every_coaching_phase_is_reported(self) -> None:
        self.assertEqual(
            list(self.section["phases"]),
            [phase.name for phase in self.definition.phases],
        )

    def test_every_value_is_a_real_cone_angle(self) -> None:
        for phase, block in self.section["phases"].items():
            self.assertEqual(len(block["rows"]), 6)
            for row in block["rows"]:
                with self.subTest(phase=phase, measure=row["measure"]):
                    self.assertGreaterEqual(row["measured"], 0.0)
                    self.assertLessEqual(row["measured"], 180.0)

    def test_the_reported_frame_is_the_graded_frame(self) -> None:
        """A reported value must describe the same solved frame the grading
        reads, or Erin's note and the number talk past each other."""
        last = len(self.result["points"]) - 1
        for phase in self.definition.phases:
            block = self.section["phases"][phase.name]
            self.assertEqual(block["frame"], round(phase.at_phase * last))

    def test_at_contact_both_thumbs_point_toward_the_ball(self) -> None:
        """Structural, not a band: her hands hold the sides of the ball, so
        each thumb ray points into the ball's hemisphere, under 90, not away
        from it. The current build reads about 68 on both hands."""
        rows = {
            row["measure"]: row["measured"]
            for row in self.section["phases"]["contact"]["rows"]
        }
        self.assertLess(rows["leftThumbToBallDegrees"], 90.0)
        self.assertLess(rows["rightThumbToBallDegrees"], 90.0)

    def test_the_finger_direction_is_mirror_symmetric_at_contact(self) -> None:
        """The two hands take a symmetric drill symmetrically ALONG THE HAND:
        wrist-to-knuckle survives the anti-mirrored finger fan because the fan
        moves fingers, not the hand's long axis. The thumbs do NOT get this
        assertion; their 20 degree split is the finding, not noise."""
        rows = {
            row["measure"]: row["measured"]
            for row in self.section["phases"]["contact"]["rows"]
        }
        self.assertLess(
            abs(rows["leftFingerUpDegrees"] - rows["rightFingerUpDegrees"]),
            5.0,
        )

    def test_the_measure_actually_reads_the_ball_argument(self) -> None:
        """The negative case, on real solved data, where the code can reach
        it: the same thumb against a ball moved 30 cm up must read a different
        angle. A mutation that ignores the ball centre reads the same."""
        contact = self.section["phases"]["contact"]
        points = self.result["points"][contact["frame"]]
        index = self.result["index"]
        centre = self.result["possession"].frames[contact["frame"]].centre
        true = measure_hand(points, index, "l", centre)

        # A fake ball placed straight along the solved thumb ray must read 0,
        # and one straight behind it must read 180. The real reading is about
        # 68, so a measure that ignores its ball argument fails all three.
        base = points[index["l_thumb1"]]
        ray = points[index["l_thumb3"]] - base
        ahead = measure_hand(points, index, "l", base + 4.0 * ray)
        behind = measure_hand(points, index, "l", base - 4.0 * ray)
        self.assertAlmostEqual(ahead["ThumbToBallDegrees"], 0.0, places=6)
        self.assertAlmostEqual(behind["ThumbToBallDegrees"], 180.0, places=6)
        self.assertGreater(true["ThumbToBallDegrees"], 5.0)
        self.assertLess(true["ThumbToBallDegrees"], 175.0)
        # And the up measures must NOT move: they take no ball at all.
        self.assertEqual(true["ThumbUpDegrees"], ahead["ThumbUpDegrees"])
        self.assertEqual(true["FingerUpDegrees"], behind["FingerUpDegrees"])

    def test_grading_is_untouched(self) -> None:
        """The report-only marker never leaks into the graded rows, and the
        graded rows never learn a new verdict from this lane."""
        assessment = self.definition.assess(self.result["measurements"])
        receipt = assessment.to_receipt()
        for phase, rows in receipt["phases"].items():
            for row in rows:
                with self.subTest(phase=phase, measure=row["measure"]):
                    self.assertIn(row["verdict"], ("below", "within", "above"))
                    self.assertIsNotNone(row["band"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
