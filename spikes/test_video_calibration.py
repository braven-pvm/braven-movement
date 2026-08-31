"""Contract tests for the calibration ingestion.

The real board footage arrives only after the shoot, so everything here is
synthetic: a rig with a KNOWN lens and a KNOWN relative pose is projected into
image points, and the fit has to find the numbers back. That is the only kind
of test that can exist before the shoot, and it is also the strongest kind,
because on real footage there is no truth to compare against.

EVERY DECOY HERE IS REACHABLE. A whole decoy set in this repository passed once
because the structure hid the fault regardless of the fix under test. So each
mutation below is applied to the STORED block a consumer actually reads, and
each is paired with the unmutated case, so a guard that can never fire and a
guard that always fires both show up.

THREE CLAIMS IN THIS FILE WERE WRONG IN A FIRST DRAFT AND ARE NOW MEASURED. The
held-out reprojection error was called the reading to judge a lens by, and a
5 percent focal error moves it by a fifth. The triangulated square was called
the direction guard, and a reversed pair pose slips past it. The board views
were varied too little to fit a lens, and the focal came back 1.9 percent wrong.
Each is now a test that states what was measured.

No solver and no footage. It runs on a hosted runner with OpenCV installed.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cv2  # noqa: E402

from video_calibration import (  # noqa: E402
    MINIMUM_SEPARATION_DEGREES,
    SCHEMA_VERSION,
    CalibrationError,
    board_movement,
    board_object_points,
    board_poses,
    check_worked_example,
    find_board,
    fit_intrinsics,
    fit_pair,
    held_out_error,
    load_calibration,
    pair_held_out_error,
    rotation_between_degrees,
    separation_degrees,
    split_half_agreement,
    split_held_out,
    triangulated_square_metres,
    worked_example,
)

ACROSS, DOWN, SQUARE = 9, 6, 0.060
# The truth every fit below has to find. Two different lenses on purpose: a rig
# where both cameras share a focal length cannot tell a per-camera fit from one
# fit copied twice.
TRUE_FOCAL = {"front": 900.0, "side": 820.0}
TRUE_PRINCIPAL = {"front": (288.0, 512.0), "side": (239.0, 425.0)}
SIZE = {"front": (576, 1024), "side": (478, 850)}
TRUE_SEPARATION_DEGREES = 70.0
# A real phone lens bends its edges. The fit has to find these back too, and a
# rig with no distortion cannot tell a working distortion model from a dead one.
TRUE_DISTORTION = np.array([-0.080, 0.020, 0.0005, -0.0005, 0.0])

# What a sub-pixel detector leaves behind on a well-shot board. It is here so
# the fit has something to be wrong about: a noiseless rig recovers its own
# parameters exactly, which proves only that the plumbing is connected.
NOISE_PIXELS = 0.05
# Enough views to fit a lens. Sixteen is not: refer to VarietyTest below.
VIEWS = 36


def camera_matrix(view: str) -> np.ndarray:
    focal = TRUE_FOCAL[view]
    principal_x, principal_y = TRUE_PRINCIPAL[view]
    return np.array([[focal, 0.0, principal_x],
                     [0.0, focal, principal_y],
                     [0.0, 0.0, 1.0]], dtype=np.float64)


def camera_pose(azimuth_degrees: float, distance_metres: float):
    """World to camera, OpenCV convention: X right, Y down, Z along the view."""
    angle = np.radians(azimuth_degrees)
    centre = np.array([distance_metres * np.sin(angle), 0.0,
                       -distance_metres * np.cos(angle)])
    forward = -centre / np.linalg.norm(centre)
    world_up = np.array([0.0, -1.0, 0.0])
    right = np.cross(world_up, forward)
    right = right / np.linalg.norm(right)
    down = np.cross(forward, right)
    rotation = np.stack([right, down, forward], axis=0)
    return rotation, -rotation @ centre


def true_pair_pose():
    """The relative pose the fit must find: front's frame into side's frame."""
    rotation_front, translation_front = camera_pose(0.0, 3.0)
    rotation_side, translation_side = camera_pose(TRUE_SEPARATION_DEGREES, 3.0)
    rotation = rotation_side @ rotation_front.T
    return rotation, translation_side - rotation @ translation_front


def synthetic_views(
    count: int = VIEWS, seed: int = 7, noise: float = NOISE_PIXELS,
    still: bool = False, narrow: bool = False,
):
    """Project a board at many poses into both cameras.

    `still` freezes the board, which is what the static-pairing route assumes
    and what `board_movement` has to tell apart from a waved one. `narrow`
    keeps the board at nearly one distance and one tilt, which is what a person
    does when nobody has told them otherwise, and VarietyTest measures the cost.
    """
    rng = np.random.default_rng(seed)
    board = board_object_points(ACROSS, DOWN, SQUARE)
    rotation_front, translation_front = camera_pose(0.0, 3.0)
    rotation_side, translation_side = camera_pose(TRUE_SEPARATION_DEGREES, 3.0)
    seen = {"front": [], "side": []}
    for _ in range(count):
        if still:
            spin = np.array([0.0, np.radians(35.0), 0.0])
            shift = np.zeros(3)
        elif narrow:
            spin = rng.uniform(-0.35, 0.35, 3) + np.array([0.0, np.radians(35.0), 0.0])
            shift = np.array([rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25),
                              rng.uniform(-0.2, 0.2)])
        else:
            spin = rng.uniform(-0.7, 0.7, 3) + np.array([0.0, np.radians(30.0), 0.0])
            shift = np.array([rng.uniform(-0.6, 0.6), rng.uniform(-0.5, 0.5),
                              rng.uniform(-1.0, 0.9)])
        world = (cv2.Rodrigues(spin)[0] @ board.T).T + shift
        for view, (rotation, translation) in (
            ("front", (rotation_front, translation_front)),
            ("side", (rotation_side, translation_side)),
        ):
            pixels, _ = cv2.projectPoints(
                world, cv2.Rodrigues(rotation)[0], translation,
                camera_matrix(view), TRUE_DISTORTION)
            pixels = pixels.reshape(-1, 2)
            seen[view].append(pixels + rng.normal(0.0, noise, pixels.shape))
    return board, seen


def fitted_rig(count: int = VIEWS, seed: int = 7, noise: float = NOISE_PIXELS):
    """A whole calibration, the way `calibrate` builds one, without any video."""
    board, seen = synthetic_views(count=count, seed=seed, noise=noise)
    fits = {view: fit_intrinsics(board, seen[view], *SIZE[view])
            for view in ("front", "side")}
    pair = fit_pair(board, seen["front"], seen["side"],
                    fits["front"], fits["side"], *SIZE["front"])
    return board, seen, fits, pair


def extrinsics_block(board, seen, fits, pair) -> dict:
    """The stored block, exactly as the file carries it. Mutations go here."""
    return {
        "fromView": "front",
        "toView": "side",
        "rotationRowMajorFromViewToView": [float(v) for v in pair["rotation"].ravel()],
        "translationMetresFromViewToView": [float(v) for v in pair["translation"]],
        "worked": worked_example(
            board, seen["front"][0], seen["side"][0],
            fits["front"], fits["side"], pair["rotation"], pair["translation"]),
    }


class BoardTest(unittest.TestCase):
    def test_the_board_is_flat_and_evenly_spaced(self):
        board = board_object_points(ACROSS, DOWN, SQUARE)

        self.assertEqual(board.shape, (ACROSS * DOWN, 3))
        self.assertTrue(np.all(board[:, 2] == 0.0), "the board is flat")
        self.assertAlmostEqual(float(np.linalg.norm(board[1] - board[0])), SQUARE)

    def test_a_square_size_of_zero_is_refused(self):
        """A zero would put every recovered length at zero and raise nothing."""
        with self.assertRaises(CalibrationError):
            board_object_points(ACROSS, DOWN, 0.0)


class IntrinsicsTest(unittest.TestCase):
    def test_the_known_lens_is_recovered(self):
        board, seen = synthetic_views()

        for view in ("front", "side"):
            fit = fit_intrinsics(board, seen[view], *SIZE[view])
            self.assertAlmostEqual(
                fit["cameraMatrix"][0, 0], TRUE_FOCAL[view],
                delta=TRUE_FOCAL[view] * 0.003)
            self.assertAlmostEqual(
                fit["cameraMatrix"][0, 2], TRUE_PRINCIPAL[view][0], delta=6.0)
            self.assertAlmostEqual(
                fit["cameraMatrix"][1, 2], TRUE_PRINCIPAL[view][1], delta=6.0)

    def test_the_known_distortion_is_recovered(self):
        """A dead distortion model would leave these at zero and still fit the
        focal length well, because the board never reaches the frame edge here."""
        board, seen = synthetic_views()

        fit = fit_intrinsics(board, seen["front"], *SIZE["front"])

        self.assertAlmostEqual(float(fit["distortion"][0]), TRUE_DISTORTION[0], delta=0.02)
        self.assertAlmostEqual(float(fit["distortion"][1]), TRUE_DISTORTION[1], delta=0.05)

    def test_the_two_cameras_are_fitted_separately(self):
        """A fit copied from one camera to the other would pass every test above
        that looks at one camera. The two true focal lengths differ by 80 px."""
        board, seen = synthetic_views()

        front = fit_intrinsics(board, seen["front"], *SIZE["front"])
        side = fit_intrinsics(board, seen["side"], *SIZE["side"])

        self.assertGreater(
            abs(front["cameraMatrix"][0, 0] - side["cameraMatrix"][0, 0]), 40.0)

    def test_k3_is_fixed_at_zero_unless_asked_for(self):
        board, seen = synthetic_views()

        fixed = fit_intrinsics(board, seen["front"], *SIZE["front"])
        free = fit_intrinsics(board, seen["front"], *SIZE["front"], free_k3=True)

        self.assertEqual(float(fixed["distortion"][4]), 0.0)
        self.assertNotEqual(float(free["distortion"][4]), 0.0)

    def test_too_few_board_views_is_refused_by_name(self):
        board, seen = synthetic_views(count=4)

        with self.assertRaises(CalibrationError) as raised:
            fit_intrinsics(board, seen["front"], *SIZE["front"])
        self.assertIn("at least 6", str(raised.exception))


class VarietyTest(unittest.TestCase):
    """Why the shoot instruction says to vary the board's distance and tilt.

    This is a MEASUREMENT, not a preference. It is a test because the number is
    the whole argument for an instruction a person has to follow while holding
    a board, and a sentence in a document would not have survived a rewrite.
    """

    def test_a_narrow_board_sequence_fits_a_worse_lens(self):
        board, narrow = synthetic_views(narrow=True)
        _, wide = synthetic_views(narrow=False)

        narrow_error = abs(
            fit_intrinsics(board, narrow["front"], *SIZE["front"])["cameraMatrix"][0, 0]
            - TRUE_FOCAL["front"])
        wide_error = abs(
            fit_intrinsics(board, wide["front"], *SIZE["front"])["cameraMatrix"][0, 0]
            - TRUE_FOCAL["front"])

        self.assertGreater(narrow_error, wide_error * 2.0)

    def test_the_fit_has_no_bias_of_its_own(self):
        """At zero detector noise every parameter comes back exactly. Whatever a
        real calibration gets wrong is the footage, not the arithmetic."""
        board, seen = synthetic_views(noise=0.0)
        true_rotation, true_translation = true_pair_pose()

        fits = {view: fit_intrinsics(board, seen[view], *SIZE[view])
                for view in ("front", "side")}
        pair = fit_pair(board, seen["front"], seen["side"],
                        fits["front"], fits["side"], *SIZE["front"])

        self.assertAlmostEqual(fits["front"]["cameraMatrix"][0, 0], 900.0, delta=0.5)
        self.assertLess(rotation_between_degrees(pair["rotation"], true_rotation), 0.01)
        self.assertLess(
            float(np.linalg.norm(pair["translation"] - true_translation)), 0.0005)

    def test_the_error_scales_with_the_detector_noise(self):
        """The finding the file's accuracyIsSetByTheFootage block carries: the
        calibration is only as good as the footage the corners came from."""
        true_rotation, _ = true_pair_pose()

        _, _, _, sharp = fitted_rig(noise=0.05)
        _, _, _, soft = fitted_rig(noise=0.30)

        sharp_error = rotation_between_degrees(sharp["rotation"], true_rotation)
        soft_error = rotation_between_degrees(soft["rotation"], true_rotation)

        self.assertLess(sharp_error, 0.5)
        self.assertGreater(soft_error, sharp_error * 2.0)


class HeldOutTest(unittest.TestCase):
    def test_the_held_out_error_is_small_on_the_right_lens(self):
        board, seen = synthetic_views()
        fitted, held = split_held_out(seen["front"])
        fit = fit_intrinsics(board, fitted, *SIZE["front"])

        error = held_out_error(board, held, fit["cameraMatrix"], fit["distortion"])

        self.assertIsNotNone(error)
        self.assertLess(error, 1.0)

    def test_a_focal_error_hides_inside_the_re_solved_pose(self):
        """THE WEAKNESS, MEASURED, AND ON THE RIGHT QUANTITY.

        A first version of this test asserted a RATIO and failed, which is how
        the framing got corrected. Six free degrees of freedom per held-out
        frame absorb most of a focal error into the board's distance, and what
        survives is an ABSOLUTE residual of about a fifth of a pixel whatever
        the footage is. On a noiseless rig that fifth of a pixel stands out
        three to one; at a realistic 0.30 pixels of detector noise it is buried
        under the noise the footage already carries. The absolute residual is
        the fact; the ratio is an artefact of how good the rig was.
        """
        board, sharp = synthetic_views(noise=0.0)
        _, real = synthetic_views(noise=0.30)

        gaps = {}
        for name, seen in (("sharp", sharp), ("real", real)):
            fitted, held = split_held_out(seen["front"])
            fit = fit_intrinsics(board, fitted, *SIZE["front"])
            honest = held_out_error(board, held, fit["cameraMatrix"], fit["distortion"])
            wrong = fit["cameraMatrix"].copy()
            wrong[0, 0] *= 1.05
            spoiled = held_out_error(board, held, wrong, fit["distortion"])
            gaps[name] = (honest, spoiled)

        for honest, spoiled in gaps.values():
            self.assertLess(spoiled - honest, 0.30,
                            "a 5 percent focal error leaves under a third of a "
                            "pixel behind, whatever the footage")
        honest_real, spoiled_real = gaps["real"]
        self.assertLess(spoiled_real, honest_real * 2.0,
                        "on real footage that residual is inside the noise")

    def test_a_gross_distortion_fault_does_not_hide(self):
        """The other half of the claim: it IS a strong reading of a gross fault.
        No rigid pose can undo a bent straight line."""
        board, seen = synthetic_views()
        fitted, held = split_held_out(seen["front"])
        fit = fit_intrinsics(board, fitted, *SIZE["front"])
        honest = held_out_error(board, held, fit["cameraMatrix"], fit["distortion"])

        wrong = fit["distortion"].copy()
        wrong[0] = -0.60
        spoiled = held_out_error(board, held, fit["cameraMatrix"], wrong)

        self.assertGreater(spoiled, honest * 10.0)

    def test_the_held_out_set_is_strided_rather_than_a_tail(self):
        """A board drifts through its poses, so a tail tests one corner of the
        range. The stride has to reach the start of the set."""
        fitted, held = split_held_out(list(range(20)))

        self.assertEqual(len(fitted) + len(held), 20)
        self.assertFalse(set(fitted) & set(held))
        self.assertLess(min(held), 10, "the held-out set reaches the first half")

    def test_a_short_set_holds_nothing_out_rather_than_holding_out_one(self):
        fitted, held = split_held_out(list(range(5)))

        self.assertEqual(len(held), 0)
        self.assertEqual(len(fitted), 5)


class SplitHalfTest(unittest.TestCase):
    """The reading that DOES judge a lens, and the mutation that earns it."""

    def test_the_gap_is_small_on_a_well_shot_board(self):
        board, seen = synthetic_views(noise=0.05)

        found = split_half_agreement(board, seen["front"], *SIZE["front"])

        self.assertIsNotNone(found)
        self.assertLess(found["focalDisagreementPercent"], 0.5)

    def test_the_gap_grows_with_the_detector_noise(self):
        """Without this the gap could be a constant and nobody would notice."""
        board, sharp = synthetic_views(noise=0.05)
        _, soft = synthetic_views(noise=0.50)

        sharp_gap = split_half_agreement(
            board, sharp["front"], *SIZE["front"])["focalDisagreementPercent"]
        soft_gap = split_half_agreement(
            board, soft["front"], *SIZE["front"])["focalDisagreementPercent"]

        self.assertGreater(soft_gap, sharp_gap * 3.0)

    def test_too_few_views_returns_nothing_rather_than_a_bad_number(self):
        board, seen = synthetic_views(count=10)

        self.assertIsNone(split_half_agreement(board, seen["front"], *SIZE["front"]))


class PairPoseTest(unittest.TestCase):
    def test_the_known_relative_pose_is_recovered(self):
        board, seen, fits, pair = fitted_rig()
        true_rotation, true_translation = true_pair_pose()

        self.assertLess(rotation_between_degrees(pair["rotation"], true_rotation), 0.5)
        self.assertLess(
            float(np.linalg.norm(pair["translation"] - true_translation)), 0.020)

    def test_the_direction_is_first_into_second_and_not_the_reverse(self):
        """THE SIGN CONVENTION, AS A DECOY THAT CAN FAIL. The reverse pose is a
        real 3 by 3 matrix and a real translation; nothing but the measurement
        below separates it from the right one."""
        _, _, _, pair = fitted_rig()
        true_rotation, true_translation = true_pair_pose()
        reverse_rotation = true_rotation.T
        reverse_translation = -true_rotation.T @ true_translation

        self.assertGreater(
            rotation_between_degrees(pair["rotation"], reverse_rotation), 10.0,
            "the decoy must be far from the truth, or this test proves nothing")
        self.assertLess(rotation_between_degrees(pair["rotation"], true_rotation), 0.5)
        self.assertGreater(
            float(np.linalg.norm(pair["translation"] - reverse_translation)), 0.5)

    def test_the_separation_angle_reads_the_rig(self):
        _, _, _, pair = fitted_rig()

        self.assertAlmostEqual(
            separation_degrees(pair["rotation"]), TRUE_SEPARATION_DEGREES, delta=0.5)

    def test_a_narrow_pair_is_below_the_minimum_separation(self):
        """The product rule this feeds: below 45 degrees the pair adds nothing."""
        rotation_front, _ = camera_pose(0.0, 3.0)
        rotation_narrow, _ = camera_pose(10.0, 3.0)

        angle = separation_degrees(rotation_narrow @ rotation_front.T)

        self.assertAlmostEqual(angle, 10.0, delta=0.5)
        self.assertLess(angle, MINIMUM_SEPARATION_DEGREES)

    def test_the_pair_held_out_error_is_small_and_rises_on_a_wrong_pose(self):
        """The pair pose is the one thing a re-solved pose cannot absorb: the
        board's pose is solved in the FIRST camera and then carried."""
        board, seen, fits, pair = fitted_rig()
        held_front, held_side = seen["front"][:4], seen["side"][:4]

        honest = pair_held_out_error(
            board, held_front, held_side, fits["front"], fits["side"],
            pair["rotation"], pair["translation"])
        spoiled = pair_held_out_error(
            board, held_front, held_side, fits["front"], fits["side"],
            pair["rotation"], pair["translation"] + np.array([0.05, 0.0, 0.0]))

        self.assertLess(honest, 1.5)
        self.assertGreater(spoiled, honest * 3.0)

    def test_unequal_view_counts_are_refused(self):
        board, seen, fits, _ = fitted_rig()

        with self.assertRaises(CalibrationError):
            fit_pair(board, seen["front"], seen["side"][:-1],
                     fits["front"], fits["side"], *SIZE["front"])


class WorkedExampleTest(unittest.TestCase):
    """The assertion every consumer runs, and the five ways it must fire.

    Each mutation rewrites the STORED block, which is what a consumer reads.
    The unmutated case is checked first, so a checker that always raises fails
    here rather than passing five times over.
    """

    def setUp(self):
        self.board, self.seen, self.fits, self.pair = fitted_rig()
        self.block = extrinsics_block(self.board, self.seen, self.fits, self.pair)

    def test_it_holds_on_an_honest_block(self):
        residual = check_worked_example(self.block)

        self.assertLess(residual, 0.010)

    def test_the_worked_points_are_not_a_restatement_of_the_pair_pose(self):
        """Both points come from a separate solvePnP, so the residual is a real
        disagreement between three fits and is never exactly zero."""
        self.assertGreater(self.block["worked"]["residualMetres"], 0.0)

    def test_a_transposed_rotation_fires(self):
        rotation = np.asarray(
            self.block["rotationRowMajorFromViewToView"]).reshape(3, 3)
        self.block["rotationRowMajorFromViewToView"] = [
            float(v) for v in rotation.T.ravel()]

        with self.assertRaises(CalibrationError):
            check_worked_example(self.block)

    def test_a_negated_translation_fires(self):
        self.block["translationMetresFromViewToView"] = [
            -v for v in self.block["translationMetresFromViewToView"]]

        with self.assertRaises(CalibrationError):
            check_worked_example(self.block)

    def test_the_reverse_direction_fires(self):
        """Storing the second-into-first pose, which is the mistake the keypoint
        schema's sync block was made for, and the one the triangulated square
        cannot see."""
        rotation = np.asarray(
            self.block["rotationRowMajorFromViewToView"]).reshape(3, 3)
        translation = np.asarray(self.block["translationMetresFromViewToView"])
        self.block["rotationRowMajorFromViewToView"] = [
            float(v) for v in rotation.T.ravel()]
        self.block["translationMetresFromViewToView"] = [
            float(v) for v in (-rotation.T @ translation)]

        with self.assertRaises(CalibrationError):
            check_worked_example(self.block)

    def test_swapped_worked_points_fire(self):
        """The two points written the wrong way round in the file."""
        worked = self.block["worked"]
        worked["pointInFromViewMetres"], worked["pointInToViewMetres"] = (
            worked["pointInToViewMetres"], worked["pointInFromViewMetres"])

        with self.assertRaises(CalibrationError):
            check_worked_example(self.block)

    def test_the_message_names_what_to_look_at(self):
        self.block["translationMetresFromViewToView"] = [
            -v for v in self.block["translationMetresFromViewToView"]]

        with self.assertRaises(CalibrationError) as raised:
            check_worked_example(self.block)
        self.assertIn("mm", str(raised.exception))
        self.assertIn("inverted", str(raised.exception))


class TriangulatedSquareTest(unittest.TestCase):
    """A gross-error check on SCALE. It is not the direction guard: measured, a
    reversed pair pose moved the recovered square by 2.8 mm on a 16-view rig,
    which is inside the band an honest fit occupies. Direction is guarded by
    WorkedExampleTest.test_the_reverse_direction_fires."""

    def test_the_known_square_is_rebuilt(self):
        board, seen, fits, pair = fitted_rig()

        found = triangulated_square_metres(
            board, ACROSS, DOWN, seen["front"][0], seen["side"][0],
            fits["front"], fits["side"], pair["rotation"], pair["translation"])

        self.assertAlmostEqual(found["medianMetres"], SQUARE, delta=0.002)

    def test_a_millimetre_for_metre_slip_is_caught(self):
        """The fault this check exists for: a board measured in millimetres and
        entered as metres puts every recovered length out by a thousand, and
        every reprojection error stays exactly where it was."""
        board, seen, fits, pair = fitted_rig()

        found = triangulated_square_metres(
            board, ACROSS, DOWN, seen["front"][0], seen["side"][0],
            fits["front"], fits["side"],
            pair["rotation"], pair["translation"] * 1000.0)

        self.assertGreater(found["medianMetres"], 1.0)
        self.assertGreater(abs(found["medianErrorMetres"]), 1.0)


class BoardMovementTest(unittest.TestCase):
    def test_a_still_board_is_called_still(self):
        board, seen = synthetic_views(count=8, still=True)
        fit = fit_intrinsics(board, seen["front"], *SIZE["front"])
        rotations, centres = board_poses(
            board, seen["front"], fit["cameraMatrix"], fit["distortion"])

        movement = board_movement(rotations, centres)

        self.assertTrue(movement["heldStill"])

    def test_a_moved_board_is_called_moved(self):
        """Without this the static-pairing route would accept a waved board and
        pair frames that are not the same instant."""
        board, seen = synthetic_views(count=8, still=False)
        fit = fit_intrinsics(board, seen["front"], *SIZE["front"])
        rotations, centres = board_poses(
            board, seen["front"], fit["cameraMatrix"], fit["distortion"])

        movement = board_movement(rotations, centres)

        self.assertFalse(movement["heldStill"])
        self.assertGreater(movement["worstPairTranslationMetres"], 0.05)

    def test_the_measured_spread_travels_beside_the_verdict(self):
        """The thresholds are chosen, not measured, so a reader must be able to
        judge them rather than trust them."""
        board, seen = synthetic_views(count=8, still=True)
        fit = fit_intrinsics(board, seen["front"], *SIZE["front"])
        rotations, centres = board_poses(
            board, seen["front"], fit["cameraMatrix"], fit["distortion"])

        movement = board_movement(rotations, centres)

        self.assertIn("worstPairTranslationMetres", movement)
        self.assertIn("toleranceTranslationMetres", movement)


class DetectorTest(unittest.TestCase):
    """The one test that exercises the image path rather than the geometry."""

    @staticmethod
    def rendered_board(square_pixels: int = 60) -> np.ndarray:
        squares_across, squares_down = ACROSS + 1, DOWN + 1
        tile = (np.indices((squares_down, squares_across)).sum(axis=0) % 2)
        board = np.kron(
            tile, np.ones((square_pixels, square_pixels), dtype=np.uint8)) * 255
        margin = square_pixels
        canvas = np.full(
            (board.shape[0] + 2 * margin, board.shape[1] + 2 * margin), 255, np.uint8)
        canvas[margin:margin + board.shape[0], margin:margin + board.shape[1]] = board
        return canvas

    def test_a_rendered_board_is_found(self):
        found = find_board(self.rendered_board(), ACROSS, DOWN)

        self.assertIsNotNone(found)
        self.assertEqual(found.shape, (ACROSS * DOWN, 2))

    def test_a_tilted_rendered_board_is_found(self):
        image = self.rendered_board()
        height, width = image.shape
        source = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
        target = np.float32([[60, 30], [width - 20, 0],
                             [width - 60, height - 30], [20, height]])
        tilted = cv2.warpPerspective(
            image, cv2.getPerspectiveTransform(source, target), (width, height),
            borderValue=255)

        found = find_board(tilted, ACROSS, DOWN)

        self.assertIsNotNone(found)
        self.assertEqual(found.shape, (ACROSS * DOWN, 2))

    def test_a_blank_image_finds_nothing(self):
        """The negative case. A detector that returned corners for anything
        would pass both tests above."""
        self.assertIsNone(
            find_board(np.full((600, 600), 200, np.uint8), ACROSS, DOWN))

    def test_the_wrong_board_size_finds_nothing(self):
        """Why the board size may have a default and the square size may not: a
        wrong board size stops the run, and a wrong square size does not."""
        self.assertIsNone(find_board(self.rendered_board(), ACROSS + 2, DOWN))


class LoadTest(unittest.TestCase):
    def setUp(self):
        board, seen, fits, pair = fitted_rig()
        self.document = {
            "schemaVersion": SCHEMA_VERSION,
            "extrinsics": extrinsics_block(board, seen, fits, pair),
        }

    def write(self, document: dict) -> Path:
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8")
        handle.write(json.dumps(document))
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return Path(handle.name)

    def test_an_honest_file_loads(self):
        loaded = load_calibration(self.write(self.document))

        self.assertEqual(loaded["schemaVersion"], SCHEMA_VERSION)

    def test_a_wrong_schema_version_is_refused(self):
        self.document["schemaVersion"] = "video-calibration-0"

        with self.assertRaises(CalibrationError):
            load_calibration(self.write(self.document))

    def test_loading_runs_the_worked_assertion(self):
        """A consumer that only calls load_calibration must still get the check.
        Without this, the checker could be correct and never reached."""
        self.document["extrinsics"]["translationMetresFromViewToView"] = [
            -v for v in self.document["extrinsics"]["translationMetresFromViewToView"]]

        with self.assertRaises(CalibrationError):
            load_calibration(self.write(self.document))


if __name__ == "__main__":
    unittest.main()
