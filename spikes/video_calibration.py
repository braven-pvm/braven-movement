"""Turn checkerboard footage from two cameras into intrinsics and a pair pose.

THE MISSING PIECE THE FINDINGS REPORT NAMES. `docs/VIDEO_CAPTURE_FINDINGS.md`
instruction 2 says a shape cannot become a number without a calibration
reference in frame. This is the other half of that instruction: the code that
reads the reference and writes down what it recovered. Without it, a board in
shot is a board in shot.

What it produces is one file per session, described in
`VIDEO_CALIBRATION_SCHEMA.md`. Read that before consuming one.

THE PROTOCOL, AND WHY IT NEEDS NO SYNC
--------------------------------------

Two passes, and they answer two different questions.

**Intrinsics** belong to a phone, its lens and its capture resolution. They do
not belong to a take. Recovering them needs the board at MANY angles and
distances, so one person waves the board in front of ONE camera for twenty
seconds. The other camera is not involved and no clock is shared, so there is
nothing to synchronise.

**The pair pose** belongs to the take, because it dies the moment a tripod is
nudged. Recovering it needs both cameras to see the board AT THE SAME INSTANT.
That normally demands sync, which is the thing this material never had. It does
not demand sync if THE BOARD DOES NOT MOVE: a still board is at the same place
in every frame, so any frame of one camera pairs with any frame of the other.
`--pairing static` takes that route and then MEASURES whether the board really
held still, because an assumption nobody checks is how a wrong number gets a
provenance stamp. `--pairing synced` is there for the day a clap exists.

WHAT THIS CANNOT DO
-------------------

- It cannot recover a pair pose the cameras did not hold. A calibration
  describes the rig at the moment it was shot. Move a tripod and it is fiction,
  and nothing in the file can detect that, so `preconditions` says it in words.
- It cannot calibrate from a metre rule. A checkerboard gives hundreds of
  sub-pixel correspondences per frame across the whole image, which is what
  fits a lens; two ends of a rule give two points and fit nothing. A
  known-object route is deliberately NOT built here, and the shoot instruction
  should ask for a printed board rather than leave the choice open.
- It cannot tell you the intrinsics are right. It can tell you what they
  predict on frames the fit never saw, which is a different and weaker claim,
  honestly labelled `heldOutReprojectionErrorPixels`.

    pixi run python video_calibration.py --session 1.0 \\
        --square-metres 0.040 \\
        --intrinsics front "F:/.../board-front.mp4" \\
        --intrinsics side  "F:/.../board-side.mp4" \\
        --pair front "F:/.../pair-front.mp4" side "F:/.../pair-side.mp4"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from build_stamp import generated_from  # noqa: E402

OUTPUT = SPIKE_DIR / "poc-output" / "video"
SCHEMA_VERSION = "video-calibration-1"

# Inner corners, which is one fewer than the squares in each direction. A wrong
# board size announces itself: the detector finds nothing and the run stops. A
# wrong SQUARE SIZE does not announce itself — every angle stays right and every
# length is wrong by that ratio — which is why `--square-metres` is required and
# this one has a default.
DEFAULT_BOARD = (9, 6)

# The two spreads that decide whether a static-pairing board really held still.
# CHOSEN, NOT MEASURED, and the file always carries the measured spread beside
# them so a reader can judge the threshold rather than trust it. A board on a
# stand holds to well under these; a board held by hand does not.
STATIC_TRANSLATION_TOLERANCE_METRES = 0.010
STATIC_ROTATION_TOLERANCE_DEGREES = 1.0

# Below this the two cameras see the same thing and the pair adds nothing. It is
# `multi_camera_fit.MINIMUM_SEPARATION_DEGREES`, imported as a number rather
# than a module because that module imports the solver.
MINIMUM_SEPARATION_DEGREES = 45.0

# One frame in this many is offered to the detector. At 30 fps, 5 gives six
# candidate frames a second, which is far more board poses than a fit needs.
DEFAULT_EVERY = 5
# Frames kept out of every fit and used only to test it. A quarter, at least
# three, because a held-out reading on one frame is an anecdote.
HELD_OUT_SHARE = 0.25
MINIMUM_HELD_OUT = 3


class CalibrationError(RuntimeError):
    """Something the operator must fix before the numbers mean anything."""


# ---------------------------------------------------------------- video input
# These four read the video exactly the way `video_keypoints.py` reads it, and
# that is a requirement rather than a convenience. Timestamps here must be the
# same numbers as timestamps there, or a calibration cannot be tied to the take
# it was shot in.


def probe_stream(path: Path) -> dict:
    done = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,avg_frame_rate", "-show_entries",
         "stream_side_data=rotation", "-of", "json", str(path)],
        capture_output=True, text=True, check=True)
    stream = json.loads(done.stdout)["streams"][0]
    rotation = 0
    for side in stream.get("side_data_list", []) or []:
        if "rotation" in side:
            rotation = int(side["rotation"])
    top, bottom = (int(v) for v in stream["avg_frame_rate"].split("/"))
    return {
        "containerWidthPixels": int(stream["width"]),
        "containerHeightPixels": int(stream["height"]),
        "rotationMetadataDegrees": rotation,
        "framesPerSecondMeasured": round(top / bottom, 4) if bottom else None,
    }


def decoded_size(path: Path) -> tuple[int, int]:
    """Read off a real decoded frame. The container size is not this.

    The front cameras of session 1.0 carry -90 rotation metadata: the container
    says 1024x576 and ffmpeg hands back 576x1024. An intrinsics matrix written
    against the container size would put the principal point outside the image.
    """
    done = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(path), "-frames:v", "1",
         "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True, check=True)
    width, height = struct.unpack(">II", done.stdout[16:24])
    return int(width), int(height)


def timestamps(path: Path) -> list[float]:
    done = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "frame=pts_time", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True)
    return [float(line.strip().rstrip(",")) for line in done.stdout.splitlines()
            if line.strip()]


def frames(path: Path, width: int, height: int):
    """Every decoded frame as RGB, streamed rather than held."""
    pipe = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(path), "-f", "rawvideo",
         "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    size = width * height * 3
    try:
        while True:
            raw = pipe.stdout.read(size)
            if len(raw) < size:
                return
            yield np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 3).copy()
    finally:
        pipe.stdout.close()
        pipe.wait()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


# ------------------------------------------------------------------- geometry
# Everything below here is pure: numpy, OpenCV, and no video and no filesystem.
# That is what lets the tests run on a machine with no footage on it, which is
# every machine except this one until the shoot happens.


def board_object_points(across: int, down: int, square_metres: float) -> np.ndarray:
    """The board's own corners, in the board's own frame, in metres.

    Z is zero for every corner because the board is flat. X runs across, Y runs
    down, and the origin is the first inner corner. Nothing here is a camera
    coordinate: these are the same numbers whatever camera looks at them.
    """
    if square_metres <= 0.0:
        raise CalibrationError("square size must be positive metres")
    grid = np.zeros((across * down, 3), dtype=np.float64)
    grid[:, :2] = np.mgrid[0:across, 0:down].T.reshape(-1, 2) * square_metres
    return grid


def find_board(grey: np.ndarray, across: int, down: int) -> np.ndarray | None:
    """The board's inner corners in this image, sub-pixel, or None.

    `findChessboardCornersSB` rather than the older detector: it refines to
    sub-pixel itself, and it survives the blur and the low bitrate that a
    messaging-grade transcode leaves behind. The findings report measured this
    material at 1.4 to 1.8 Mbps and 576p-class.
    """
    found, corners = cv2.findChessboardCornersSB(
        grey, (across, down), flags=cv2.CALIB_CB_EXHAUSTIVE | cv2.CALIB_CB_ACCURACY)
    if not found:
        return None
    return corners.reshape(-1, 2).astype(np.float64)


def reprojection_error_pixels(
    object_points: np.ndarray, image_points: np.ndarray,
    rotation_vector: np.ndarray, translation_vector: np.ndarray,
    camera_matrix: np.ndarray, distortion: np.ndarray,
) -> float:
    """Root mean square distance, in pixels, between seen and predicted corners.

    Per POINT, not per coordinate: each corner contributes one distance. That is
    what `cv2.calibrateCamera` returns as well, so the fit error and the held-out
    error below are the same quantity and may be compared.
    """
    predicted, _ = cv2.projectPoints(
        object_points, rotation_vector, translation_vector, camera_matrix, distortion)
    gap = predicted.reshape(-1, 2) - image_points.reshape(-1, 2)
    return float(np.sqrt(np.mean(np.sum(gap * gap, axis=1))))


def rotation_between_degrees(first: np.ndarray, second: np.ndarray) -> float:
    """The angle of the rotation that takes `first` to `second`, in degrees."""
    trace = float(np.trace(first @ second.T))
    return float(np.degrees(np.arccos(np.clip((trace - 1.0) / 2.0, -1.0, 1.0))))


def separation_degrees(rotation: np.ndarray) -> float:
    """The angle between the two cameras' viewing directions.

    A camera looks along +Z in its own frame. The second camera's viewing
    direction, expressed in the FIRST camera's frame, is the third ROW of the
    first-to-second rotation, so the angle against the first camera's own +Z is
    `arccos(rotation[2, 2])`. Written down because the third row reads like a
    typing error for the third column and is not one.
    """
    return float(np.degrees(np.arccos(np.clip(rotation[2, 2], -1.0, 1.0))))


def fit_intrinsics(
    object_points: np.ndarray, seen: list[np.ndarray],
    width: int, height: int, free_k3: bool = False,
) -> dict:
    """Fit one camera's lens from many views of the board.

    K3 IS FIXED AT ZERO UNLESS ASKED FOR. The third radial term needs the board
    at the very edge of the frame in many poses to be identified at all, and on
    twenty handheld frames it absorbs noise and then repays it as a wild
    correction near the border. A term that is not identified by the data is not
    a measurement of the lens.
    """
    if len(seen) < 6:
        raise CalibrationError(
            f"only {len(seen)} usable board views; a lens fit needs at least 6 "
            "and does better with 20. Wave the board slower and closer.")
    objects = [object_points.astype(np.float32)] * len(seen)
    images = [view.reshape(-1, 1, 2).astype(np.float32) for view in seen]
    flags = 0 if free_k3 else cv2.CALIB_FIX_K3
    rms, camera_matrix, distortion, rotations, translations = cv2.calibrateCamera(
        objects, images, (width, height), None, None, flags=flags)
    return {
        "cameraMatrix": np.asarray(camera_matrix, dtype=np.float64),
        "distortion": np.asarray(distortion, dtype=np.float64).ravel(),
        "rotationVectors": [np.asarray(r, dtype=np.float64).reshape(3) for r in rotations],
        "translationVectors": [np.asarray(t, dtype=np.float64).reshape(3) for t in translations],
        "fitReprojectionErrorPixels": float(rms),
        "framesFitted": len(seen),
    }


def held_out_error(
    object_points: np.ndarray, seen: list[np.ndarray],
    camera_matrix: np.ndarray, distortion: np.ndarray,
) -> float | None:
    """What the fitted lens predicts on frames the fit never saw.

    The pose of each held-out board is re-solved, because a frame the fit never
    saw has no pose from it. That re-solve is also this reading's WEAKNESS, and
    it was measured rather than assumed: inflating the fitted focal length by 5
    percent leaves behind an ABSOLUTE residual of about a fifth of a pixel,
    because six free degrees of freedom absorb the rest into the board's
    distance. On a noiseless rig that fifth of a pixel stands out three to one;
    at a realistic 0.30 pixels of detector noise it is inside the noise the
    footage already carries and moves the reading by less than half again.

    THE ABSOLUTE RESIDUAL IS THE FACT AND THE RATIO IS NOT. A first version of
    this note quoted "0.207 to 0.252 pixels", which is the ratio on one rig, and
    a test written to that ratio failed on a sharper rig. Quote the residual.

    So this number is a WEAK instrument for the lens. It is a strong one for
    gross faults — a board size entered wrong, a view mixed up between cameras,
    a detector that found a pattern in noise — because those cannot be absorbed
    by any pose. `split_half_agreement` is the reading to judge the lens by, and
    `pair_held_out_error` is the reading to judge the pair pose by.
    """
    if not len(seen):
        return None
    errors = []
    for view in seen:
        ok, rotation_vector, translation_vector = cv2.solvePnP(
            object_points, view.reshape(-1, 1, 2), camera_matrix, distortion)
        if not ok:
            continue
        errors.append(reprojection_error_pixels(
            object_points, view, rotation_vector, translation_vector,
            camera_matrix, distortion))
    return float(np.sqrt(np.mean(np.square(errors)))) if errors else None


def split_half_agreement(
    object_points: np.ndarray, seen: list[np.ndarray],
    width: int, height: int, free_k3: bool = False,
) -> dict | None:
    """Fit the same lens twice, on disjoint halves, and report the disagreement.

    THIS IS THE INSTRUMENT FOR THE LENS, and the held-out reprojection error is
    not.

    **THE "ABOUT 1.4 TIMES" THIS DOCSTRING USED TO GIVE WAS A SEED ARTEFACT.**
    It was measured on seeds 0 to 9 of a 36-view rig, where it held at 1.36 to
    1.37 across a tenfold range of detector noise — and that stability is real
    and is a property of THOSE BOARD POSES, not of the method. Re-measured on
    three independent seed sets at the same three noise levels:

        seeds  0-9    ratio of means 1.37 / 1.36 / 1.37
        seeds 10-19   ratio of means 1.16 / 1.12 / 1.11
        seeds 20-29   ratio of means 2.43 / 2.45 / 2.49

    Stable to two decimals WITHIN a seed set and swinging by more than double
    ACROSS them. Over fifty seeds at 0.15 px the ratio of means is 1.70, and the
    PER-SEED ratio has a median of 1.43 with an interquartile range of 0.48 to
    3.91 and extremes of 0.03 and 56.6. An independent review measured the same
    shape on its own rig and got different figures — 1.67, 2.25 and 3.16 across
    its three seed sets, 2.24 over fifty — which is the point rather than a
    discrepancy: the factor is not a property anybody can quote.

    **So do not divide by it.** What survives, and is worth having:

    - The gap SCALES with the detector noise, so it tracks the thing that
      drives the error.
    - Within one set of board poses the ratio does not depend on the noise at
      all, over a tenfold range.
    - It is the right ORDER of the true error and never a multiplier.
    - **It is not a ceiling.** The gap exceeded the true error in 29 of 50
      runs here and in 36 of 50 in the review, so a reader who treats it as a
      bound will be optimistic about two times in five.

    Why it works where the held-out error does not: `solvePnP` re-solves six
    degrees of freedom per held-out frame and absorbs most of a focal error into
    the board's distance, so the reprojection barely moves. Two independent fits
    of the same fixed quantity have nothing to absorb it into.
    """
    if len(seen) < 12:
        return None
    first = fit_intrinsics(object_points, seen[0::2], width, height, free_k3)
    second = fit_intrinsics(object_points, seen[1::2], width, height, free_k3)
    focal_first = float(first["cameraMatrix"][0, 0])
    focal_second = float(second["cameraMatrix"][0, 0])
    middle = (focal_first + focal_second) / 2.0
    return {
        "focalXPixelsFirstHalf": round(focal_first, 3),
        "focalXPixelsSecondHalf": round(focal_second, 3),
        "focalDisagreementPercent": round(
            abs(focal_first - focal_second) / middle * 100.0, 4),
        "principalDisagreementPixels": round(float(np.linalg.norm(
            first["cameraMatrix"][:2, 2] - second["cameraMatrix"][:2, 2])), 3),
        "note": (
            "Two fits of one lens on disjoint halves of the board views. It is "
            "the right ORDER of the true focal error and NOT a multiplier: on a "
            "synthetic rig the ratio of gap to true error is stable to two "
            "decimals within one set of board poses across a tenfold range of "
            "detector noise, and swings from 1.11 to 2.49 between seed sets, "
            "with a per-seed interquartile range of 0.48 to 3.91. Do not divide "
            "by it. It is also NOT a ceiling: it exceeded the true error in 29 "
            "of 50 runs. What it does reliably is scale with the noise."
        ),
    }


def board_poses(
    object_points: np.ndarray, seen: list[np.ndarray],
    camera_matrix: np.ndarray, distortion: np.ndarray,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Where the board sat, in this camera's own frame, for each view."""
    rotations, centres = [], []
    for view in seen:
        ok, rotation_vector, translation_vector = cv2.solvePnP(
            object_points, view.reshape(-1, 1, 2), camera_matrix, distortion)
        if not ok:
            raise CalibrationError("a board pose failed to solve on a detected board")
        rotations.append(cv2.Rodrigues(rotation_vector)[0])
        centres.append(np.asarray(translation_vector, dtype=np.float64).reshape(3))
    return rotations, centres


def board_movement(
    rotations: list[np.ndarray], centres: list[np.ndarray]
) -> dict:
    """How far the board moved across these frames, as seen by one camera.

    Worst PAIR, not spread from the first frame. A reference frame that is
    itself the outlier hides half the movement, and there are at most forty
    frames here so the pairs are free.
    """
    worst_metres, worst_degrees = 0.0, 0.0
    for first in range(len(centres)):
        for second in range(first + 1, len(centres)):
            worst_metres = max(
                worst_metres, float(np.linalg.norm(centres[first] - centres[second])))
            worst_degrees = max(
                worst_degrees, rotation_between_degrees(rotations[first], rotations[second]))
    return {
        "worstPairTranslationMetres": round(worst_metres, 6),
        "worstPairRotationDegrees": round(worst_degrees, 4),
        "toleranceTranslationMetres": STATIC_TRANSLATION_TOLERANCE_METRES,
        "toleranceRotationDegrees": STATIC_ROTATION_TOLERANCE_DEGREES,
        "heldStill": bool(
            worst_metres <= STATIC_TRANSLATION_TOLERANCE_METRES
            and worst_degrees <= STATIC_ROTATION_TOLERANCE_DEGREES),
    }


def fit_pair(
    object_points: np.ndarray,
    seen_first: list[np.ndarray], seen_second: list[np.ndarray],
    first: dict, second: dict, width: int, height: int,
) -> dict:
    """Fit the pose of the second camera relative to the first.

    THE DIRECTION IS MEASURED, NOT ASSUMED. `cv2.stereoCalibrate` returns the
    rotation and translation that carry a point from the FIRST camera's own 3D
    frame into the SECOND camera's:

        pointInSecond = rotation @ pointInFirst + translation

    That was confirmed against a synthetic rig with a known relative pose before
    this file was written, and `test_video_calibration.py` holds the check with
    the opposite direction as a decoy that fails. Prose about direction is
    exactly what failed in version 1 of the keypoint schema.

    The intrinsics are FIXED. They were fitted on a moving board that filled the
    frame; the pair frames are one board pose in one place, which is far too
    little to re-identify a lens, and letting the optimiser adjust them here
    would let a pair-pose error hide inside a focal length.
    """
    if len(seen_first) != len(seen_second):
        raise CalibrationError("the two views have unequal numbers of paired boards")
    if len(seen_first) < 2:
        raise CalibrationError(
            f"only {len(seen_first)} paired board views; the pair pose needs at least 2")
    objects = [object_points.astype(np.float32)] * len(seen_first)
    images_first = [v.reshape(-1, 1, 2).astype(np.float32) for v in seen_first]
    images_second = [v.reshape(-1, 1, 2).astype(np.float32) for v in seen_second]
    rms, _, _, _, _, rotation, translation, _, _ = cv2.stereoCalibrate(
        objects, images_first, images_second,
        first["cameraMatrix"], first["distortion"],
        second["cameraMatrix"], second["distortion"],
        (width, height), flags=cv2.CALIB_FIX_INTRINSIC)
    return {
        "rotation": np.asarray(rotation, dtype=np.float64).reshape(3, 3),
        "translation": np.asarray(translation, dtype=np.float64).reshape(3),
        "fitReprojectionErrorPixels": float(rms),
        "framesFitted": len(seen_first),
    }


def pair_held_out_error(
    object_points: np.ndarray,
    seen_first: list[np.ndarray], seen_second: list[np.ndarray],
    first: dict, second: dict, rotation: np.ndarray, translation: np.ndarray,
) -> float | None:
    """Predict the SECOND camera's corners from the FIRST camera's view of them.

    The board pose is solved in the first camera only. The pair pose then carries
    it into the second camera and the corners are projected there, so the number
    that comes back is the pair pose's own error and nothing else's. A frame in
    this set was never in the pair fit.
    """
    if not len(seen_first):
        return None
    errors = []
    for view_first, view_second in zip(seen_first, seen_second):
        ok, rotation_vector, translation_vector = cv2.solvePnP(
            object_points, view_first.reshape(-1, 1, 2),
            first["cameraMatrix"], first["distortion"])
        if not ok:
            continue
        board_in_first = cv2.Rodrigues(rotation_vector)[0]
        # Compose: board -> first camera, then first camera -> second camera.
        board_in_second = rotation @ board_in_first
        origin_in_second = rotation @ np.asarray(
            translation_vector, dtype=np.float64).reshape(3) + translation
        errors.append(reprojection_error_pixels(
            object_points, view_second, cv2.Rodrigues(board_in_second)[0],
            origin_in_second, second["cameraMatrix"], second["distortion"]))
    return float(np.sqrt(np.mean(np.square(errors)))) if errors else None


def triangulated_square_metres(
    object_points: np.ndarray, across: int, down: int,
    view_first: np.ndarray, view_second: np.ndarray,
    first: dict, second: dict, rotation: np.ndarray, translation: np.ndarray,
) -> dict:
    """Rebuild the board in 3D from the pair, and measure a square of it.

    WHAT THIS IS AND IS NOT. The square size entered the fit through the object
    points, so recovering it is PARTLY CIRCULAR and it is not evidence that the
    scale is right. It is a GROSS-ERROR CHECK ON SCALE: a millimetre entered
    where a metre belongs, or a board whose rows and columns were swapped,
    returns a number that is obviously not the square.

    IT IS NOT THE DIRECTION GUARD, and an earlier draft of this docstring said
    it was. Measured: reversing the pair pose on the 70-degree rig moved the
    recovered square by 2.8 mm on 16 board views and 17.0 mm on a wider set — a
    reversed pose still triangulates to roughly board-sized geometry, so this
    check would pass it about as often as not. Direction is guarded by
    `check_worked_example`, which fails a reversed pose by a factor of a
    hundred. Each guard catches what it catches.
    """
    ideal_first = cv2.undistortPoints(
        view_first.reshape(-1, 1, 2), first["cameraMatrix"], first["distortion"])
    ideal_second = cv2.undistortPoints(
        view_second.reshape(-1, 1, 2), second["cameraMatrix"], second["distortion"])
    projection_first = np.hstack([np.eye(3), np.zeros((3, 1))])
    projection_second = np.hstack([rotation, translation.reshape(3, 1)])
    homogeneous = cv2.triangulatePoints(
        projection_first, projection_second,
        ideal_first.reshape(-1, 2).T, ideal_second.reshape(-1, 2).T)
    points = (homogeneous[:3] / homogeneous[3]).T
    grid = points.reshape(down, across, 3)
    spans = np.concatenate([
        np.linalg.norm(np.diff(grid, axis=1), axis=2).ravel(),
        np.linalg.norm(np.diff(grid, axis=0), axis=2).ravel(),
    ])
    known = float(np.linalg.norm(object_points[1] - object_points[0]))
    return {
        "medianMetres": round(float(np.median(spans)), 6),
        "p90Metres": round(float(np.percentile(spans, 90)), 6),
        "knownMetres": round(known, 6),
        "medianErrorMetres": round(float(np.median(spans)) - known, 6),
    }


# ------------------------------------------------------------- the file shape


def intrinsics_block(fit: dict, width: int, height: int, free_k3: bool) -> dict:
    """Every field names its space and its units, per the keypoint schema.

    There is no field called `fx` and no bare array of five numbers. A reader
    who does not know whether a focal length is in pixels or millimetres cannot
    silently pick the wrong one here.
    """
    matrix = fit["cameraMatrix"]
    coefficients = list(fit["distortion"]) + [0.0] * 5
    return {
        "focalXPixels": round(float(matrix[0, 0]), 4),
        "focalYPixels": round(float(matrix[1, 1]), 4),
        "principalXPixel": round(float(matrix[0, 2]), 4),
        "principalYPixel": round(float(matrix[1, 2]), 4),
        "imageWidthPixels": width,
        "imageHeightPixels": height,
        "distortion": {
            "k1": round(float(coefficients[0]), 8),
            "k2": round(float(coefficients[1]), 8),
            "p1": round(float(coefficients[2]), 8),
            "p2": round(float(coefficients[3]), 8),
            "k3": round(float(coefficients[4]), 8),
        },
        "distortionModel": (
            "OpenCV five-coefficient plumb bob, in the order k1 k2 p1 p2 k3. "
            + ("k3 was fitted." if free_k3 else
               "k3 was FIXED AT ZERO because twenty handheld frames do not "
               "identify it; refer to fit_intrinsics.")
        ),
        "imageSizeNote": (
            "The DECODED frame size, read off a real frame. It is not the "
            "container size: a view with rotation metadata decodes transposed, "
            "and a principal point written against the container lands outside "
            "the image."
        ),
    }


def worked_example(
    object_points: np.ndarray,
    view_first: np.ndarray, view_second: np.ndarray,
    first: dict, second: dict, rotation: np.ndarray, translation: np.ndarray,
) -> dict:
    """One board corner, located in each camera's frame INDEPENDENTLY.

    THIS IS A CROSS-CHECK AND NOT A RESTATEMENT. Both points come from
    `solvePnP` run separately in each camera, so neither is computed from the
    pair pose being tested. A consumer that asserts

        rotation @ pointInFromViewMetres + translation == pointInToViewMetres

    is therefore asking whether the pair fit agrees with the two single-camera
    fits, and the assertion CAN FAIL. That is the difference between this and
    the keypoint schema's sync worked example, which is derived from the offset
    it guards and can only catch a later edit.

    The corner is the board's own origin, index zero, because it is the one
    corner a reader can point at in a picture of the board.
    """
    ok_first, rotation_first, translation_first = cv2.solvePnP(
        object_points, view_first.reshape(-1, 1, 2),
        first["cameraMatrix"], first["distortion"])
    ok_second, rotation_second, translation_second = cv2.solvePnP(
        object_points, view_second.reshape(-1, 1, 2),
        second["cameraMatrix"], second["distortion"])
    if not (ok_first and ok_second):
        raise CalibrationError("the worked example's board pose failed to solve")
    corner = object_points[0]
    in_first = cv2.Rodrigues(rotation_first)[0] @ corner + np.asarray(
        translation_first, dtype=np.float64).reshape(3)
    in_second = cv2.Rodrigues(rotation_second)[0] @ corner + np.asarray(
        translation_second, dtype=np.float64).reshape(3)
    residual = float(np.linalg.norm(rotation @ in_first + translation - in_second))
    return {
        "note": (
            "The board's origin corner, located in each camera's own 3D frame by "
            "a separate solvePnP. Neither point is computed from the pair pose, "
            "so the assertion below tests the pair pose rather than restating it."
        ),
        "landmark": "board inner corner index 0",
        "pointInFromViewMetres": [round(float(v), 6) for v in in_first],
        "pointInToViewMetres": [round(float(v), 6) for v in in_second],
        "assertion": (
            "rotationRowMajorFromViewToView @ pointInFromViewMetres + "
            "translationMetresFromViewToView == pointInToViewMetres"
        ),
        "residualMetres": round(residual, 6),
    }


def check_worked_example(extrinsics: dict, tolerance_metres: float = 0.010) -> float:
    """Run the assertion the file tells every consumer to run on load.

    Returns the residual in metres so a caller can report it. Raises when the
    stored pair pose does not carry the stored point onto the stored point,
    which is what an inverted direction, a transposed rotation or a negated
    translation each produce.

    The tolerance is ten millimetres and it is a CONSUMER tolerance, not a
    quality bar: it is loose enough that a fit with an honest residual passes and
    tight enough that any sign error fails by a factor of a hundred. Judge the
    fit by `residualMetres` and the held-out errors, never by this passing.
    """
    rotation = np.asarray(
        extrinsics["rotationRowMajorFromViewToView"], dtype=np.float64).reshape(3, 3)
    translation = np.asarray(
        extrinsics["translationMetresFromViewToView"], dtype=np.float64).reshape(3)
    worked = extrinsics["worked"]
    in_first = np.asarray(worked["pointInFromViewMetres"], dtype=np.float64)
    in_second = np.asarray(worked["pointInToViewMetres"], dtype=np.float64)
    residual = float(np.linalg.norm(rotation @ in_first + translation - in_second))
    if residual > tolerance_metres:
        raise CalibrationError(
            f"the pair pose does not carry its own worked point: residual "
            f"{residual * 1000.0:.1f} mm against a tolerance of "
            f"{tolerance_metres * 1000.0:.1f} mm. The stored rotation or "
            "translation is inverted, transposed or negated."
        )
    return residual


def load_calibration(path: Path) -> dict:
    """Read a calibration file and run the checks it asks a consumer to run.

    Every consumer runs the same checks because they live here rather than in
    each consumer's memory. A file that fails one raises rather than returning
    numbers that look fine.
    """
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("schemaVersion") != SCHEMA_VERSION:
        raise CalibrationError(
            f"{path} is {document.get('schemaVersion')!r}, not {SCHEMA_VERSION!r}")
    check_worked_example(document["extrinsics"])
    return document


# ------------------------------------------------------------------- assembly


def split_held_out(views: list, share: float = HELD_OUT_SHARE) -> tuple[list, list]:
    """Take every fourth view for the held-out set, never the last few.

    STRIDED, NOT A TAIL. A board waved in front of a camera drifts through its
    poses, so the last quarter of the frames is the last quarter of the poses,
    and a fit tested only there is tested on one corner of its own range. Every
    fourth frame samples the same range the fit saw.
    """
    if len(views) < MINIMUM_HELD_OUT * 2:
        return views, []
    stride = max(2, int(round(1.0 / share)))
    held = [v for n, v in enumerate(views) if n % stride == stride - 1]
    fitted = [v for n, v in enumerate(views) if n % stride != stride - 1]
    if len(held) < MINIMUM_HELD_OUT:
        return views, []
    return fitted, held


def detect_in_video(
    path: Path, across: int, down: int, every: int, limit: int
) -> tuple[list[dict], dict]:
    """Every board this video shows, with the frame's own PTS timestamp."""
    stream = probe_stream(path)
    width, height = decoded_size(path)
    stamps = timestamps(path)
    found: list[dict] = []
    for index, frame in enumerate(frames(path, width, height)):
        if index % every:
            continue
        if index >= len(stamps):
            break
        corners = find_board(cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY), across, down)
        if corners is None:
            continue
        found.append({
            "ptsSeconds": round(stamps[index], 6),
            "frameIndex": index,
            "corners": corners,
        })
        if len(found) >= limit:
            break
    stream.update({"decodedWidthPixels": width, "decodedHeightPixels": height})
    return found, stream


def camera_block(
    view: str, path: Path, stream: dict, fit: dict,
    held_out_pixels: float | None, used: list[dict], held: list[dict],
    free_k3: bool, split_half: dict | None,
) -> dict:
    return {
        "view": view,
        "videoFile": path.name,
        "videoSha256": sha256(path),
        "containerWidthPixels": stream["containerWidthPixels"],
        "containerHeightPixels": stream["containerHeightPixels"],
        "rotationMetadataDegrees": stream["rotationMetadataDegrees"],
        "intrinsics": intrinsics_block(
            fit, stream["decodedWidthPixels"], stream["decodedHeightPixels"], free_k3),
        "boardViewsFitted": len(used),
        "boardViewsHeldOut": len(held),
        "ptsSecondsFitted": [row["ptsSeconds"] for row in used],
        "ptsSecondsHeldOut": [row["ptsSeconds"] for row in held],
        "fitReprojectionErrorPixels": round(fit["fitReprojectionErrorPixels"], 4),
        "heldOutReprojectionErrorPixels": (
            round(held_out_pixels, 4) if held_out_pixels is not None else None),
        "splitHalfAgreement": split_half,
        "errorNote": (
            "THREE READINGS, AND THEY ARE NOT INTERCHANGEABLE. "
            "fitReprojectionErrorPixels is the objective the optimiser "
            "minimised, so it certifies nothing on its own. "
            "heldOutReprojectionErrorPixels is a WEAK reading of the lens, "
            "because solvePnP re-solves six degrees of freedom per held-out "
            "frame and absorbs most of a focal error into the board's distance: "
            "a 5 percent focal error leaves under a third of a pixel behind, "
            "which is inside the noise of real footage. It is a strong reading "
            "of gross faults, which no pose can absorb. "
            "splitHalfAgreement is the reading to judge the LENS by: two fits "
            "on disjoint halves. It is the right ORDER of the true focal error "
            "and NOT a multiplier — the ratio swings from 1.11 to 2.49 between "
            "seed sets — and it is not a ceiling."
        ),
    }


def build_document(
    session_id: str, across: int, down: int, square_metres: float,
    cameras: list[dict], extrinsics: dict, pairing: dict,
) -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "sessionId": session_id,
        "note": (
            "Intrinsics per camera and the pair's relative pose, for session "
            f"{session_id}. Refer to VIDEO_CALIBRATION_SCHEMA.md before "
            "consuming this: it says what a consumer may and may not assume, "
            "and it names the checks load_calibration runs."
        ),
        "board": {
            "kind": "checkerboard",
            "innerCornersAcross": across,
            "innerCornersDown": down,
            "squareSizeMetres": square_metres,
            "note": (
                "INNER corners, one fewer than the squares in each direction. "
                "The square size was supplied by the operator and is the only "
                "quantity here that nothing in the footage can check: every "
                "angle stays correct and every length scales with it."
            ),
        },
        "cameras": cameras,
        "extrinsics": extrinsics,
        "pairing": pairing,
        "accuracyIsSetByTheFootage": {
            "note": (
                "Measured on a synthetic 36-view rig, five seeds a row, with "
                "the corner detector's noise as the only variable. The fit has "
                "no bias of its own: at zero noise it recovers every parameter "
                "exactly. Everything below is the footage's noise coming out "
                "the other end."
            ),
            "rows": [
                {"detectorNoisePixels": 0.30, "focalErrorPercent": 0.25,
                 "pairRotationErrorDegrees": 1.23, "pairTranslationErrorMillimetres": 42.1},
                {"detectorNoisePixels": 0.15, "focalErrorPercent": 0.12,
                 "pairRotationErrorDegrees": 0.61, "pairTranslationErrorMillimetres": 21.0},
                {"detectorNoisePixels": 0.05, "focalErrorPercent": 0.04,
                 "pairRotationErrorDegrees": 0.20, "pairTranslationErrorMillimetres": 7.0},
            ],
            "whatItMeansForTheShoot": (
                "A pair rotation error of one degree puts about 50 mm of error "
                "into a point triangulated at three metres. Sub-pixel corner "
                "detection on a 576p messaging transcode is not 0.05 pixels. "
                "Instruction 11 of VIDEO_CAPTURE_FINDINGS.md — camera "
                "originals, not messaging transcodes — therefore buys "
                "calibration accuracy as well as sharpness, which is more than "
                "that instruction claimed for itself."
            ),
        },
        "preconditions": [
            "The cameras did not move between this calibration and the take it "
            "is applied to. Nothing in this file can detect a nudged tripod. "
            "Re-shoot the board if a camera is touched.",
            "The intrinsics belong to a phone, a lens and a capture resolution. "
            "Applying them to footage shot at another resolution is wrong and "
            "the imageWidthPixels and imageHeightPixels fields are how a "
            "consumer notices.",
            "The square size in metres was measured by a person with a rule. "
            "Every length this calibration yields is proportional to it.",
        ],
        "tool": {
            "name": "video_calibration.py",
            "library": "OpenCV",
            "libraryVersion": cv2.__version__,
            "detector": "findChessboardCornersSB, exhaustive and accurate",
        },
        "generatedFrom": generated_from(),
    }


def calibrate(
    session_id: str, square_metres: float, board: tuple[int, int],
    intrinsics_videos: dict[str, Path], pair_videos: dict[str, Path],
    every: int, limit: int, free_k3: bool, offset_seconds: float | None,
) -> dict:
    across, down = board
    object_points = board_object_points(across, down, square_metres)
    views = list(pair_videos)
    if len(views) != 2:
        raise CalibrationError("the pair needs exactly two views")

    cameras, fits, streams = [], {}, {}
    for view in views:
        path = intrinsics_videos[view]
        print(f"  {view}: reading {path.name} for the lens")
        detected, stream = detect_in_video(path, across, down, every, limit)
        print(f"    {len(detected)} board views found")
        fitted, held = split_held_out(detected)
        fit = fit_intrinsics(
            object_points, [row["corners"] for row in fitted],
            stream["decodedWidthPixels"], stream["decodedHeightPixels"], free_k3)
        error = held_out_error(
            object_points, [row["corners"] for row in held],
            fit["cameraMatrix"], fit["distortion"])
        split_half = split_half_agreement(
            object_points, [row["corners"] for row in detected],
            stream["decodedWidthPixels"], stream["decodedHeightPixels"], free_k3)
        fits[view], streams[view] = fit, stream
        cameras.append(camera_block(
            view, path, stream, fit, error, fitted, held, free_k3, split_half))
        print(f"    fit {fit['fitReprojectionErrorPixels']:.3f} px, "
              f"held out {error if error is None else round(error, 3)} px, "
              f"split half {'n/a' if split_half is None else str(split_half['focalDisagreementPercent']) + ' %'}")

    first, second = views
    paired, pairing = pair_frames(
        object_points, pair_videos, fits, across, down, every, limit, offset_seconds)
    fitted_pairs, held_pairs = split_held_out(paired)
    pair = fit_pair(
        object_points,
        [row[first] for row in fitted_pairs], [row[second] for row in fitted_pairs],
        fits[first], fits[second],
        streams[first]["decodedWidthPixels"], streams[first]["decodedHeightPixels"])
    held_pixels = pair_held_out_error(
        object_points,
        [row[first] for row in held_pairs], [row[second] for row in held_pairs],
        fits[first], fits[second], pair["rotation"], pair["translation"])
    sample = (held_pairs or fitted_pairs)[0]
    extrinsics = {
        "fromView": first,
        "toView": second,
        "rotationRowMajorFromViewToView": [
            round(float(v), 8) for v in pair["rotation"].ravel()],
        "translationMetresFromViewToView": [
            round(float(v), 6) for v in pair["translation"]],
        "directionNote": (
            f"These carry a point from the {first} camera's own 3D frame into "
            f"the {second} camera's. Refer to worked below: it is an assertion "
            "a consumer runs, because prose about direction is what failed in "
            "version 1 of the keypoint schema."
        ),
        "baselineMetres": round(float(np.linalg.norm(pair["translation"])), 6),
        "separationDegrees": round(separation_degrees(pair["rotation"]), 3),
        "minimumSeparationDegrees": MINIMUM_SEPARATION_DEGREES,
        "separationSufficient": bool(
            separation_degrees(pair["rotation"]) >= MINIMUM_SEPARATION_DEGREES),
        "separationNote": (
            "Below the minimum the two cameras see the same thing and the pair "
            "adds nothing. The threshold is multi_camera_fit's "
            "MINIMUM_SEPARATION_DEGREES, which its own spike measured."
        ),
        "boardViewsFitted": pair["framesFitted"],
        "boardViewsHeldOut": len(held_pairs),
        "fitReprojectionErrorPixels": round(pair["fitReprojectionErrorPixels"], 4),
        "heldOutReprojectionErrorPixels": (
            round(held_pixels, 4) if held_pixels is not None else None),
        "worked": worked_example(
            object_points, sample[first], sample[second],
            fits[first], fits[second], pair["rotation"], pair["translation"]),
        "triangulatedSquare": triangulated_square_metres(
            object_points, across, down, sample[first], sample[second],
            fits[first], fits[second], pair["rotation"], pair["translation"]),
    }
    print(f"  pair {first} -> {second}: baseline "
          f"{extrinsics['baselineMetres']:.3f} m, separation "
          f"{extrinsics['separationDegrees']:.1f} deg, held out "
          f"{extrinsics['heldOutReprojectionErrorPixels']} px")
    return build_document(
        session_id, across, down, square_metres, cameras, extrinsics, pairing)


def pair_frames(
    object_points: np.ndarray, pair_videos: dict[str, Path], fits: dict,
    across: int, down: int, every: int, limit: int, offset_seconds: float | None,
) -> tuple[list[dict], dict]:
    """Put the two cameras' board views side by side, and say how.

    Static pairing takes any frame against any frame and then MEASURES whether
    the board held still, because that is the assumption the whole route rests
    on. Synced pairing needs a measured offset and matches by timestamp.
    """
    first, second = list(pair_videos)
    detected = {}
    for view, path in pair_videos.items():
        print(f"  {view}: reading {path.name} for the pair")
        rows, _ = detect_in_video(path, across, down, every, limit)
        print(f"    {len(rows)} board views found")
        if not rows:
            raise CalibrationError(
                f"no board found in {path.name}. The pair pose cannot be fitted "
                "without the board visible to both cameras at once.")
        detected[view] = rows

    if offset_seconds is None:
        movement = {}
        for view in (first, second):
            rotations, centres = board_poses(
                object_points, [row["corners"] for row in detected[view]],
                fits[view]["cameraMatrix"], fits[view]["distortion"])
            movement[view] = board_movement(rotations, centres)
        if not all(m["heldStill"] for m in movement.values()):
            moved = {v: m for v, m in movement.items() if not m["heldStill"]}
            raise CalibrationError(
                "static pairing was asked for and the board MOVED: "
                + "; ".join(
                    f"{view} worst pair {m['worstPairTranslationMetres'] * 1000:.1f} mm "
                    f"and {m['worstPairRotationDegrees']:.2f} deg"
                    for view, m in moved.items())
                + ". Re-shoot with the board on a stand, or supply "
                  "--offset-seconds and pair by the clock."
            )
        count = min(len(detected[first]), len(detected[second]))
        rows = [
            {first: detected[first][n]["corners"],
             second: detected[second][n]["corners"],
             "ptsSecondsFirst": detected[first][n]["ptsSeconds"],
             "ptsSecondsSecond": detected[second][n]["ptsSeconds"]}
            for n in range(count)
        ]
        return rows, {
            "method": "static",
            "note": (
                "The board did not move, so any frame of one camera pairs with "
                "any frame of the other and no clock is shared. The movement "
                "below is the measurement that licenses that."
            ),
            "boardMovement": movement,
        }

    by_time = {round(row["ptsSeconds"], 6): row for row in detected[second]}
    stamps = np.array(sorted(by_time))
    rows = []
    for row in detected[first]:
        want = row["ptsSeconds"] + offset_seconds
        nearest = stamps[int(np.argmin(np.abs(stamps - want)))]
        if abs(nearest - want) > 0.017:
            continue
        mate = by_time[nearest]
        rows.append({
            first: row["corners"], second: mate["corners"],
            "ptsSecondsFirst": row["ptsSeconds"],
            "ptsSecondsSecond": mate["ptsSeconds"],
        })
    if not rows:
        raise CalibrationError(
            f"no frame pairs within half a frame at an offset of "
            f"{offset_seconds} s. Check the sign: it is added to a {first} "
            f"timestamp to reach the {second} clock.")
    return rows, {
        "method": "synced",
        "offsetSecondsFirstToSecond": offset_seconds,
        "note": (
            f"A {first} timestamp plus this offset is the matching {second} "
            "timestamp. Pairs further apart than half a frame were dropped."
        ),
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True, help="the session id, e.g. 1.0")
    parser.add_argument("--square-metres", required=True, type=float,
                        help="the checkerboard square, measured with a rule. "
                             "REQUIRED: a default would put a wrong scale in a "
                             "file that looks right.")
    parser.add_argument("--board", default="9x6",
                        help="INNER corners across by down, e.g. 9x6")
    parser.add_argument("--intrinsics", nargs=2, action="append", metavar=("VIEW", "PATH"),
                        required=True, help="a moving-board clip for one camera")
    parser.add_argument("--pair", nargs=4, required=True,
                        metavar=("VIEW_A", "PATH_A", "VIEW_B", "PATH_B"),
                        help="the two clips that see the board at once")
    parser.add_argument("--offset-seconds", type=float, default=None,
                        help="pair by the clock instead of assuming a still "
                             "board; added to a VIEW_A timestamp to reach VIEW_B")
    parser.add_argument("--every", type=int, default=DEFAULT_EVERY)
    parser.add_argument("--max-boards", type=int, default=40)
    parser.add_argument("--free-k3", action="store_true",
                        help="fit the third radial term; refer to fit_intrinsics")
    parser.add_argument("--out", default=None)
    arguments = parser.parse_args(argv[1:])

    across, down = (int(v) for v in arguments.board.lower().split("x"))
    intrinsics_videos = {view: Path(path) for view, path in arguments.intrinsics}
    view_a, path_a, view_b, path_b = arguments.pair
    pair_videos = {view_a: Path(path_a), view_b: Path(path_b)}
    missing = [
        str(p) for p in list(intrinsics_videos.values()) + list(pair_videos.values())
        if not p.exists()
    ]
    if missing:
        raise SystemExit("these files do not exist:\n  " + "\n  ".join(missing))
    for view in pair_videos:
        if view not in intrinsics_videos:
            raise SystemExit(f"view {view!r} is in the pair and has no --intrinsics clip")

    document = calibrate(
        arguments.session, arguments.square_metres, (across, down),
        intrinsics_videos, pair_videos, arguments.every, arguments.max_boards,
        arguments.free_k3, arguments.offset_seconds)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    where = Path(arguments.out) if arguments.out else (
        OUTPUT / f"calibration-{arguments.session}.json")
    where.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    # Read it back through the consumer path, so a file that cannot be loaded
    # never leaves this process claiming success.
    residual = check_worked_example(load_calibration(where)["extrinsics"])
    print(f"\nworked example holds to {residual * 1000.0:.2f} mm")
    print(f"written -> {where}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
