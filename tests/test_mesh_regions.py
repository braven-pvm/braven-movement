"""Guards for the rule that says WHICH part of the athlete is inside the ball.

A count without a location is half a finding. On 2026-09-04 the chest pass's
release frame put 150 vertices 17.08 mm inside the ball while every fingertip
was 31 to 67 mm outside it, and the instrument could only say "150". This is
the half that names the part.
"""

import sys
import unittest
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_DIR))

from mesh_regions import (  # noqa: E402
    FOREARM,
    HAND,
    HEAD,
    LEG,
    TORSO,
    UNKNOWN,
    UPPER_ARM,
    region_of,
    side_of,
    summarise_inside,
)


class RegionOfTest(unittest.TestCase):
    def test_the_rig_s_own_bone_names_map_to_parts(self):
        self.assertEqual(FOREARM, region_of("lowerarm_l"))
        self.assertEqual(UPPER_ARM, region_of("upperarm_r"))
        self.assertEqual(UPPER_ARM, region_of("clavicle_l"))
        self.assertEqual(TORSO, region_of("spine_03"))
        self.assertEqual(TORSO, region_of("pelvis"))
        self.assertEqual(HEAD, region_of("head"))
        self.assertEqual(HEAD, region_of("neck_01"))
        self.assertEqual(LEG, region_of("thigh_r"))
        self.assertEqual(HAND, region_of("hand_l"))

    def test_a_finger_group_is_a_hand_and_not_an_unknown(self):
        """`index_01_l` must not fall through to `unknown`.

        The finger and hand tests are disjoint, so their ORDER is not
        load-bearing: an earlier version of this test claimed it was, and a
        mutation that swapped the two rules left the suite green. That is what
        a claim about code the code does not depend on looks like.
        """
        for group in ("thumb_01_l", "index_02_r", "middle_03_l",
                      "ring_01_r", "pinky_02_l"):
            self.assertEqual(HAND, region_of(group), group)

    def test_an_unrecognised_group_is_unknown_and_not_folded_into_a_neighbour(self):
        """A rig that moved underneath must be visible, not absorbed.

        Folding an unknown group into the nearest region would report a
        confident body part for a vertex nobody has classified.
        """
        self.assertEqual(UNKNOWN, region_of("tail_01"))
        self.assertEqual(UNKNOWN, region_of(""))
        self.assertEqual(UNKNOWN, region_of("some_new_bone"))

    def test_left_and_right_are_kept_apart(self):
        """A left forearm through the ball is a different finding from a right."""
        self.assertEqual("l", side_of("lowerarm_l"))
        self.assertEqual("r", side_of("upperarm_r"))
        self.assertEqual("", side_of("spine_03"))


class SummariseTest(unittest.TestCase):
    def test_a_clean_drill_reports_NOTHING(self):
        """Every vertex outside the ball must produce an empty report.

        This is the guard that matters most. An instrument that reports a
        region for a drill with no intersection would send the movement lane
        after a fault that is not there, and the 127 clean stills in this pack
        are the population it runs against.
        """
        clean = [("lowerarm_l", 0.031), ("spine_03", 0.008), ("hand_r", 0.0)]

        summary = summarise_inside(clean)

        self.assertEqual(0, summary["verticesInside"])
        self.assertEqual({}, summary["byRegion"])
        self.assertIsNone(summary["deepestRegion"])
        self.assertEqual(0.0, summary["deepestMm"])

    def test_a_planted_intersection_names_the_right_region_and_side(self):
        """The chest pass's shape: fingers clear, something else 17 mm in."""
        planted = [
            ("index_01_l", 0.062), ("middle_02_r", 0.064),   # fingers, clear
            ("lowerarm_l", -0.01708), ("lowerarm_l", -0.012),
            ("lowerarm_r", -0.009),
        ]

        summary = summarise_inside(planted)

        self.assertEqual(3, summary["verticesInside"])
        self.assertEqual("forearm l", summary["deepestRegion"])
        self.assertAlmostEqual(-17.08, summary["deepestMm"], places=2)
        self.assertEqual(2, summary["byRegion"]["forearm l"]["vertices"])
        self.assertEqual(1, summary["byRegion"]["forearm r"]["vertices"])
        self.assertNotIn("hand l", summary["byRegion"],
                         "a vertex OUTSIDE the ball must not be summarised")

    def test_the_spread_is_reported_beside_the_leader(self):
        """150 vertices in one region and 150 across three are different faults.

        Naming only the deepest would make them read the same.
        """
        spread = [("spine_03", -0.002), ("lowerarm_l", -0.02),
                  ("upperarm_l", -0.003)]

        summary = summarise_inside(spread)

        self.assertEqual("forearm l", summary["deepestRegion"])
        self.assertEqual(3, len(summary["byRegion"]),
                         "every region carrying an inside vertex is listed")

    def test_a_vertex_exactly_on_the_surface_is_not_inside(self):
        """Zero is contact. Counting it would inflate every clean figure."""
        self.assertEqual(0, summarise_inside([("hand_l", 0.0)])["verticesInside"])

    def test_the_exact_group_is_kept_because_hand_is_too_coarse(self):
        """A palm, a thumb web and a finger base are all "hand".

        The movement lane measured the THUMB CHAIN inside the ball on joint
        centres while this lane measured the thumb TIP 44 mm outside on skin.
        Both readings can hold — a tip is not a palm, and a joint centre is not
        skin — and only the group name separates them. Reporting "hand" would
        have left that reconciliation unmeasurable.
        """
        samples = [("hand_l", -0.017), ("thumb_01_l", -0.004),
                   ("index_01_l", -0.001)]

        summary = summarise_inside(samples)

        self.assertEqual({"hand l": {"vertices": 3, "deepestMm": -17.0}},
                         summary["byRegion"])
        self.assertEqual(3, len(summary["byGroup"]),
                         "the three parts of the hand stay apart")
        self.assertEqual(-17.0, summary["byGroup"]["hand_l"]["deepestMm"])
        self.assertEqual(-4.0, summary["byGroup"]["thumb_01_l"]["deepestMm"])


if __name__ == "__main__":
    unittest.main()
