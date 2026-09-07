"""Read 2D keypoints from one camera view, per PTS timestamp.

Writes the file described in `VIDEO_KEYPOINT_SCHEMA.md`, which the movement
lane and the rendering lane agreed before either had data. Read that first: it
says what a consumer may and may not assume, and several of its rules exist
because a version of them was already got wrong once.

The three traps in this material, and what is done about each:

- **Rotation.** The front cameras carry -90 metadata, so their containers say
  1024x576 and their decoded frames are 576x1024. Frames come through ffmpeg,
  which applies it, and the decoded size is read off a real frame rather than
  reasoned about. It goes in the file, because normalised coordinates are
  meaningless without it.
- **Variable frame rate.** The side cameras run 30.012 fps against the front's
  exact 30.000. Every record carries the container's own timestamp for that
  frame. Nothing here multiplies an index by a rate.
- **Frames that are not footage.** The pose tool emits confident landmarks for
  a smeared frame, because a smeared body is still body-shaped. Each record
  carries a quality reading judged against the clip's OWN median, so a consumer
  can tell a camera being picked up from a person standing still.

LICENCE, RESOLVED FROM THE CARD AND NOT FROM THE PACKAGE. The bundle itself
carries NO licence text — it is a zip holding two .tflite files and nothing
else, and neither carries a copyright string. The Model Card BlazePose GHUM 3D
says "LICENSED UNDER: Apache License, Version 2.0" on page 2, and that is the
authority. Both facts travel in every file this writes, because the second is
what makes the model usable and the first is what makes checking it necessary.

The same card names 3D pose measurement in scope, puts people beyond about four
metres and multi-person scenes OUT of scope, and states that Z is not metric
but up to scale. All three are carried in the file.

    pixi run python video_keypoints.py --view side --set 0.1
    pixi run python video_keypoints.py --all
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
SAMPLES = Path("F:/Repositories/braven-movement/.assets/video-samples/session-1.0")
MODEL = Path("F:/Repositories/braven-movement/.assets/models/pose_landmarker_heavy.task")
OUTPUT = SPIKE_DIR / "poc-output" / "video"

# Where the sync came from, and how well. Positive is added to a timestamp in
# THIS file to reach the reference view's clock. Refer to the schema: the
# direction is carried as a worked example because prose about it failed once.
REFERENCE_VIEW = "front"
# THE PAIRING IS BETWEEN FILES, NOT BETWEEN SETS, AND THE FILE NAMES ARE WRONG.
#
# `front 0.1.mp4` and `side 0.2.mp4` ARE THE SAME RUN. `front 0.2.mp4` and
# `side 0.1.mp4` are not shown to be a pair by anything measured here. The four
# files were named as two sets and at least one of those names is wrong.
#
# THE SOURCE FILES ARE NOT RENAMED. They are Marius's assets, every path in the
# tree points at them, and renaming is his decision. The mapping is recorded
# here instead, and every consumer reads the mapping rather than the name.
#
# WHY THE MEASUREMENT IS A FRAME COUNT AND NOT A NUMBER OF SECONDS. The two
# cameras do not run at the same rate — 33.3330 ms per frame on the front,
# 33.3220 ms on the side — so a constant FRAME offset appears as a time offset
# that drifts, from -0.1704 s at the first anchor to -0.1763 s fifteen seconds
# later. That is a fifth of a frame and it is real. Seconds are DERIVED here,
# never stored as the measurement, and a consumer that wants one takes it from
# the mapping at its own frame:
#
#     side_pts[front_index - 5]  is the side time for front frame front_index
#
# TWO OFFSETS WERE WITHDRAWN BEFORE THIS ONE, both on set 0.1 as labelled:
# +1.0 s (which did pair corresponding moments, contrary to what a version of
# this file said) and -0.7295 s, which paired two DIFFERENT catches one toss
# cycle apart. Refer to docs/KNOWN_ISSUES.md.
PAIRS = {
    "front 0.1 + side 0.2": {
        "referenceFile": "front 0.1.mp4",
        "otherFile": "side 0.2.mp4",
        # side index = front index + frameOffsetToReference
        "frameOffsetToReference": -5,
        "methodKind": "shared-event",
        "framePeriodSeconds": {"front 0.1.mp4": 0.033333, "side 0.2.mp4": 0.033322},
        # TWO ANCHORS, both a ball meeting hands — a transition of one frame,
        # with no judgement in it — and 11.03 s apart.
        "anchors": [
            {"event": "first catch, ball into hands",
             "referenceIndex": 274, "referenceSeconds": 9.1333,
             "otherIndex": 269, "otherSeconds": 8.9630,
             "derivedSecondsOffset": -0.1704},
            {"event": "overhead catch, ball into hands",
             "referenceIndex": 605, "referenceSeconds": 20.1667,
             "otherIndex": 600, "otherSeconds": 19.9920,
             "derivedSecondsOffset": -0.1746},
        ],
        # A CHECK, NOT AN ANCHOR: it sits between the two and adds no span.
        "checks": [
            {"event": "second clap, hands meet",
             "referenceIndex": 534, "referenceSeconds": 17.8000,
             "otherIndex": 529, "otherSeconds": 17.6264,
             "derivedSecondsOffset": -0.1736},
        ],
        # REPORTED AND SET ASIDE, because a withheld disagreement is a lie by
        # omission. The FIRST clap gives a frame difference of 4, not 5.
        "setAside": [
            {"event": "first clap, hands meet",
             "referenceIndex": 175, "referenceSeconds": 5.8333,
             "otherIndex": 171, "otherSeconds": 5.6977,
             "frameDifference": 4,
             "why": ("A CLASP IS SOFT. 'Nearly together' and 'together' are one "
                     "frame apart and the call is a judgement, in both views; "
                     "calling the side one frame earlier gives 5 and agrees "
                     "with everything else. A ball meeting hands has no such "
                     "ambiguity, which is why the two catches are the anchors "
                     "and every clap is only a check. The disagreement is "
                     "recorded rather than resolved by picking the frame that "
                     "suits the answer.")},
        ],
        "derivedNote": (
            "The seconds above are DERIVED from each file's own pts and are not "
            "the measurement. They drift by about 6 ms across 15 s because the "
            "two cameras' frame periods differ by 11 microseconds. The "
            "measurement is the frame offset, which does not drift."),
    },
}

# FILES WHOSE PARTNER IS NOT ESTABLISHED. Not "unpaired" — nothing here shows
# they lack a partner, only that none is measured.
#
# `front 0.2.mp4` and `side 0.1.mp4` were tried against each other with the
# same rule and FAILED IT. Two targeted anchors gave frame differences of 77
# and 75, and the events do not match in kind: at the first, the side's ball
# arrives horizontally from the left as a fed pass while the front's descends
# from the top as a self toss; at the second, the side catches two-handed and
# the front one-handed.
#
# **THAT ATTEMPT CANNOT BE RE-READ, AND SO IT IS NOT EVIDENCE.** No frame index
# and no timestamp of any of the four frames tried was written down, here or
# anywhere else in the tree. "77 and 75" therefore cannot be checked, corrected
# or reproduced by anyone, including me: it is a recollection of a reading, not
# a reading. It is kept above because it is what was done, and it is labelled
# here because a number without its inputs must not be quoted as a result.
#
# It changes nothing about the conclusion, which does not rest on it: the
# pairing of these two files is UNKNOWN, and it would still be unknown if the
# attempt had never happened. What replaces the attempt is the fine event
# ledger of `front 0.2.mp4`, which is a queued unit and is NOT done; refer to
# `spikes/video-annotations/event-ledger-0.2.json`, which records NOT READ with
# its reason.
#
# THE SECOND ANCHOR WAS FOUND BY LOOKING WHERE THE FIRST PREDICTED ONE, and a
# catch found where an offset predicted a catch is not evidence in a clip of
# catches. That is how -0.7295 was published.
#
# NO ELIMINATION ARGUMENT IS MADE. "There are four files, so the other two must
# pair" is a guess until a ledger says so, and how many files each camera
# produced is not recorded anywhere in this tree.
PAIRING_UNKNOWN = ("front 0.2.mp4", "side 0.1.mp4")


def pair_for(view: str, set_id: str) -> tuple[str, dict] | tuple[None, None]:
    """The pair this file belongs to, and its role — or nothing."""
    name = f"{view} {set_id}.mp4"
    for key, pair in PAIRS.items():
        if name in (pair["referenceFile"], pair["otherFile"]):
            return key, pair
    return None, None


def paired_files(name: str) -> tuple[str, str, int] | None:
    """The pair a file belongs to, as (reference, other, frameOffset).

    THE ARGUMENT IS A FILE NAME, NOT A SET. Every consumer in this repository
    used to load "both views of set X", and that is exactly the assumption the
    mislabel destroyed: there is no set whose two same-named files are a pair.
    A consumer that still asks by set gets None here and must say so rather
    than reach for a field.
    """
    for pair in PAIRS.values():
        if name in (pair["referenceFile"], pair["otherFile"]):
            return (pair["referenceFile"], pair["otherFile"],
                    pair["frameOffsetToReference"])
    return None


PTS_TOLERANCE_SECONDS = 0.0005


def frame_offset_of(sync: dict, frames: list | None = None) -> int:
    """The frame offset of a sync block, WITH ITS OWN ANCHORS CHECKED.

    Every consumer must run this check, and the check must live in ONE place.
    Two copies of it existed, one in each consumer, and neither was held by a
    test: they read the offset out of a written artefact, so mutating the
    offset in PAIRS above changed nothing either of them could see. A guard no
    mutation has failed is a guard nobody has checked.

    It RAISES rather than asserting. `assert` disappears under `python -O`, and
    this is a check on data, not on a programming mistake.

    TWO CHECKS, AND THE SECOND NEEDS THE FRAMES. The index arithmetic is the
    measurement and holds on its own. But the schema tells a consumer to assert
    `other_pts[referenceIndex + frameOffsetToReference] == otherSeconds`, and
    this only compared integers, so the schema sentence was not true of the code
    it described. Pass `frames` (the other file's own frame list) and the row's
    recorded `otherSeconds` is checked against the frame it actually names.
    That is what catches an index pair copied correctly into a block whose
    seconds came from somewhere else."""
    offset = int(sync["frameOffsetToReference"])
    for row in sync["anchors"] + sync["checks"]:
        if row["otherIndex"] != row["referenceIndex"] + offset:
            raise SystemExit(
                "the sync block's own anchor does not satisfy its frame "
                f"offset of {offset}: {row['event']} has reference index "
                f"{row['referenceIndex']} and other index {row['otherIndex']}, "
                f"a difference of {row['otherIndex'] - row['referenceIndex']}.")
        if frames is None or "otherSeconds" not in row:
            continue
        index = row["referenceIndex"] + offset
        if not 0 <= index < len(frames):
            raise SystemExit(
                f"{row['event']}: index {index} is outside the paired file, "
                f"which has {len(frames)} frames.")
        found = float(frames[index]["ptsSeconds"])
        if abs(found - float(row["otherSeconds"])) > PTS_TOLERANCE_SECONDS:
            raise SystemExit(
                f"{row['event']}: the block says frame {index} of the paired "
                f"file is at {row['otherSeconds']} s, and that frame is at "
                f"{found:.4f} s. The indices and the seconds disagree.")
    return offset


def keypoint_file(view: str, set_id: str) -> Path:
    """Where the writer puts a view's keypoints. The writer owns this name, so
    every consumer asks the writer for it rather than rebuilding the string."""
    return OUTPUT / f"keypoints-{view}-{set_id}.json"


def load_keypoints(video_name: str) -> dict:
    """The keypoint file for a named VIDEO FILE, whatever set its name claims.
    The name is only a label: `side 0.2.mp4` is the partner of `front 0.1.mp4`.
    Both consumers call this, so neither can invent a different mapping."""
    view, rest = video_name.split(" ", 1)
    path = keypoint_file(view, rest.removesuffix(".mp4"))
    if not path.exists():
        raise SystemExit(f"{path} is missing; run video_keypoints.py first")
    return json.loads(path.read_text(encoding="utf-8"))


def pair_slug(pair_key: str) -> str:
    """The file-name form of a pair key. ONE definition, because two
    consumers name artefacts by it: the lift writes `lift-3d-<slug>.json`
    and the elbow curve reads exactly that file. Two copies of this rule
    would let one of them drift and read a file the other never wrote."""
    return pair_key.replace(" + ", "-and-").replace(" ", "_").replace(".mp4", "")


def refuse_by_set(set_id: str) -> str:
    """What to tell a caller that asked for a set rather than a pair."""
    established = ", ".join(f"{p['referenceFile']} + {p['otherFile']}"
                            for p in PAIRS.values())
    return (f"set {set_id} is not a pair. THE FILE NAMES ARE WRONG: the only "
            f"established pairing is {established}, at a constant FRAME offset. "
            f"{PAIRING_UNKNOWN[0]} and {PAIRING_UNKNOWN[1]} have no established "
            "partner. Ask for a pair rather than a set; refer to PAIRS in "
            "video_keypoints.py.")


# THE FLOOR A FRAME-PAIRED OFFSET REACHES, kept for consumers that need an
# uncertainty in seconds. One frame, because the measurement is which frame
# each view's contact falls in.
SYNC_UNCERTAINTY_SECONDS = 0.0333

# HOW THE OFFSET WAS ARRIVED AT, as a field of its own rather than a phrase
# inside a sentence — the same reason a threshold declares its kind separately.
# A consumer deciding whether to trust a pairing needs the grade, and a grade it
# has to parse out of prose is not a field.
METHOD_KINDS = ("clap", "shared-event", "eye", "correlation", "unknown")

# WHAT THIS BLOCK MUST NEVER SAY. Until 2026-09-04 the writer stamped
# "two visual events matched by eye; no clap exists in this material" into every
# file it wrote. A clap WAS later found in the front recording of set 0.1, at
# 5.800 s and 17.835 s, so the writer had been stamping a false claim into new
# artefacts. Nothing in this function measures whether a clap exists, so nothing
# in this function may say. The block states WHAT WAS DONE, never what was ruled
# out.
SYNC_METHOD_NOTE = (
    "WHAT THIS BLOCK CARRIES. For `front 0.1.mp4` and `side 0.2.mp4`: a "
    "constant FRAME offset of -5, side index = front index - 5, measured on "
    "two ball-into-hands anchors 11.03 s apart and checked on a third event. "
    "For `front 0.2.mp4` and `side 0.1.mp4`: NO PARTNER IS ESTABLISHED, and "
    "that is not a claim that they lack one. Seconds are derived here and are "
    "never the measurement.\n\n"
    "WHAT IS WITHDRAWN, and why every one of them failed the same way. This "
    "block once asserted that no clap existed in this material; two were later "
    "found in `front 0.1.mp4`, at 5.800 s and 17.835 s. It then carried +1.0 s "
    "for set 0.1 as labelled, and then -0.7295 s graded 'shared event' — which "
    "named a frame in each view where a ball meets hands and they were "
    "DIFFERENT CATCHES, one toss cycle apart. THE CAUSE OF ALL THREE WAS THE "
    "SAME: the file names are wrong, so nobody was measuring a bad offset; "
    "everybody was measuring between two files that are not a pair. Refer to "
    "'The alignment ranked a sync clap above every real catch' in "
    "docs/KNOWN_ISSUES.md."
)
# The camera is picked up after this, measured per frame by the rendering lane.
USABLE_TO = {("front", "0.1"): 25.7}

ATHLETE = {
    "heightMetres": 1.77,
    "wingspanMetres": 1.82,
    "oneArmReachMetres": 0.77,
    "ballDiameterMetres": 0.223,
    "source": "supplied by Marius, 2026-08-28; ball is netball size 5, 220 to 226 mm",
}

MODEL_LICENCE_SOURCE = (
    "Model Card BlazePose GHUM 3D, page 2, LICENSED UNDER: Apache License, "
    "Version 2.0. Read 2026-08-28 from "
    "https://storage.googleapis.com/mediapipe-assets/"
    "Model%20Card%20BlazePose%20GHUM%203D.pdf — the card is the authority. "
    "THE BUNDLE ITSELF CARRIES NO LICENCE TEXT: it is a zip holding "
    "pose_detector.tflite and pose_landmarks_detector.tflite and nothing "
    "else, and both were scanned for embedded metadata and carry no copyright "
    "or licence string. That finding stands: the card says what the bundle "
    "should have said."
)
# From the same card, and both are shoot requirements rather than notes.
MODEL_SCOPE = {
    "intendedUses": "3D pose measurements (angles and distances) is named in scope",
    "outOfScope": (
        "people further than about 4 metres from the camera; multi-person "
        "scenes, since the model tracks ONE person"
    ),
    "depthNote": (
        "the card states the Z coordinate is not metric but up to scale, "
        "fitted from synthetic GHUM data"
    ),
    "source": "Model Card BlazePose GHUM 3D, read 2026-08-28",
}


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
    """Read off a real decoded frame. The container size is not this."""
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


# How much the frame steps may vary and still count as constant. TEN
# MICROSECONDS, and the number is measured rather than chosen: on this material
# the front cameras spread 1.0 us across two distinct step values, which is the
# container's own time-base quantisation of 1/30 s, and the side cameras spread
# 200.0 us across five. Ten sits an order of magnitude above the quantisation
# and an order of magnitude below the real variation.
#
# A first attempt used half a millisecond and called the VARIABLE side cameras
# constant, because 200 us is comfortably inside 500. A threshold that cannot
# see the thing it exists to detect is worse than the hardcoded comparison it
# replaced.
CONSTANT_RATE_TOLERANCE_SECONDS = 1e-5


def constant_rate(stamps: list[float]) -> bool:
    """True when the frame steps are all the same, whatever the rate is.

    Comparing the measured rate against 30.0 would call a camera locked at 25
    or 60 variable, and would call these side cameras constant if they happened
    to average 30.000.
    """
    if len(stamps) < 3:
        return True
    steps = np.diff(np.asarray(stamps, dtype=np.float64))
    return bool((steps.max() - steps.min()) < CONSTANT_RATE_TOLERANCE_SECONDS)


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


def sharpness(grey: np.ndarray) -> float:
    """Variance of the Laplacian: high on a crisp frame, low on a smeared one."""
    middle = grey.astype(np.float32)
    laplace = (
        -4.0 * middle[1:-1, 1:-1]
        + middle[:-2, 1:-1] + middle[2:, 1:-1]
        + middle[1:-1, :-2] + middle[1:-1, 2:]
    )
    return float(laplace.var())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def landmark_names(landmarker_module) -> list[str]:
    return [name.name.lower() for name in landmarker_module.PoseLandmark]


def landmark_edges(vision_module, names: list[str]) -> list[list[str]]:
    """Edges as pairs of NAMES.

    Indices would silently rewire the skeleton the day a model reorders its
    landmarks, and an overlay would draw a limb through a chest with nothing
    failing. The rendering lane asked for names and they are right.
    """
    edges = []
    for connection in vision_module.PoseLandmarksConnections.POSE_LANDMARKS:
        edges.append([names[connection.start], names[connection.end]])
    return edges


def _sync_inputs(view: str, set_id: str) -> tuple[bool, dict]:
    """What the pair table says about this file.

    ONE DEFINITION, because there are two callers — `extract`, which writes a
    new file, and `restamp`, which corrects an existing one. A re-stamp that
    read the table its own way would be a second definition of the same thing,
    and the two would drift the first time either changed.
    """
    key, pair = pair_for(view, set_id)
    if pair is None:
        return False, {}
    name = f"{view} {set_id}.mp4"
    is_reference = name == pair["referenceFile"]
    return True, {"key": key, "pair": pair, "isReference": is_reference,
                  "file": name}


def _sync_block(view: str, set_id: str, measured: bool, sync: dict) -> dict:
    """What is known about placing this file on the other view's clock.

    THE MEASUREMENT IS A FRAME COUNT. `frameOffsetToReference` is added to a
    frame INDEX in this file to reach the reference file's index, and the
    consumer assertion is an index one:

        other_pts[reference_index + frameOffsetToReference]

    Seconds appear only as DERIVED values beside their anchors. They are not
    the measurement and they drift: the two cameras' frame periods differ by
    11 microseconds, so a constant frame offset shows as a time offset moving
    about 6 ms across 15 s. Two offsets in seconds have already been published
    from this material and withdrawn.
    """
    block = {
        "referenceView": REFERENCE_VIEW,
        "measured": measured,
        "file": f"{view} {set_id}.mp4",
    }
    if not measured:
        block["pairedWith"] = None
        block["frameOffsetToReference"] = None
        block["methodKind"] = "unknown"
        block["note"] = (
            f"NO PARTNER IS ESTABLISHED for {block['file']}. This is not a "
            "claim that it has none. THE FILE NAMES ARE WRONG: "
            "`front 0.1.mp4` pairs with `side 0.2.mp4`, measured at a constant "
            "frame offset. The remaining two files were tried against each "
            "other under the same rule and failed it — two targeted anchors "
            "gave frame differences of 77 and 75 (RECORDED WITHOUT THEIR "
            "INPUTS: no frame index or time of the four frames tried was "
            "written down, so that reading cannot be re-done and is not "
            "evidence), and the events did not match "
            "in kind. Do not pair this file with anything on a clock. Refer to "
            "PAIRING_UNKNOWN in video_keypoints.py and to "
            "spikes/video-annotations/event-ledger-<set>.json."
        )
        return block

    pair, is_reference = sync["pair"], sync["isReference"]
    other = pair["referenceFile"] if not is_reference else pair["otherFile"]
    block["pairedWith"] = other
    block["pairKey"] = sync["key"]
    # ZERO FOR THE REFERENCE FILE BY DEFINITION, and the measured count for the
    # other. The sign is the one in the table: other index = reference index +
    # frameOffsetToReference.
    block["frameOffsetToReference"] = (
        0 if is_reference else pair["frameOffsetToReference"])
    block["framePeriodSeconds"] = pair["framePeriodSeconds"][block["file"]]
    block["methodKind"] = pair["methodKind"]
    block["method"] = (
        "the frame in which a ball first meets her hands, read in both files "
        "by index from the container's own timestamp list")
    block["anchors"] = pair["anchors"]
    block["checks"] = pair["checks"]
    block["setAside"] = pair["setAside"]
    block["derivedNote"] = pair["derivedNote"]
    block["offsetUncertaintySeconds"] = SYNC_UNCERTAINTY_SECONDS
    block["methodNote"] = SYNC_METHOD_NOTE
    return block


def extract(view: str, set_id: str, git_commit: str, tree_clean: bool) -> dict:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    path = SAMPLES / f"{view} {set_id}.mp4"
    stream = probe_stream(path)
    width, height = decoded_size(path)
    stamps = timestamps(path)
    names = landmark_names(vision)

    options = vision.PoseLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(MODEL)),
        running_mode=vision.RunningMode.VIDEO,
        num_poses=1,
        output_segmentation_masks=False,
    )

    records, sharpnesses, lumas = [], [], []
    started = time.perf_counter()
    with vision.PoseLandmarker.create_from_options(options) as landmarker:
        for index, frame in enumerate(frames(path, width, height)):
            if index >= len(stamps):
                break
            pts = stamps[index]
            grey = frame[:, :, 1]
            sharpnesses.append(sharpness(grey))
            lumas.append(float(grey.mean()))
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            found = landmarker.detect_for_video(image, int(round(pts * 1000)))
            record = {
                "ptsSeconds": round(pts, 6),
                "frameIndex": index,
                "detected": bool(found.pose_landmarks),
            }
            if found.pose_landmarks:
                record["landmarks"] = [
                    {
                        "name": names[n],
                        "xNormalizedImage": round(float(p.x), 6),
                        "yNormalizedImage": round(float(p.y), 6),
                        "zNormalizedImageRelative": round(float(p.z), 6),
                        "xPixel": round(float(p.x) * width, 2),
                        "yPixel": round(float(p.y) * height, 2),
                        "visibility": round(float(p.visibility), 4),
                        "presence": round(float(p.presence), 4),
                    }
                    for n, p in enumerate(found.pose_landmarks[0])
                ]
                record["worldLandmarks"] = [
                    {
                        "name": names[n],
                        "xWorldMetres": round(float(p.x), 5),
                        "yWorldMetres": round(float(p.y), 5),
                        "zWorldMetres": round(float(p.z), 5),
                    }
                    for n, p in enumerate(found.pose_world_landmarks[0])
                ]
            records.append(record)

    # Quality is judged against this clip's OWN median. One absolute threshold
    # condemns the softer camera everywhere and catches nothing on the sharper.
    median = float(np.median(sharpnesses)) if sharpnesses else 1.0
    for record, value, luma in zip(records, sharpnesses, lumas):
        share = value / median if median > 0 else 0.0
        record["frame_quality"] = round(share, 4)
        record["luma"] = round(luma, 1)
        # The rendering lane's definition, so it exists once rather than twice:
        # half the reference sharpness, or too dark to read.
        #
        # THE REFERENCE DIFFERS FROM THEIRS AND THE NUMBER MOVES WITH IT. They
        # judge against the median of a SHEET, a dozen mostly-settled frames,
        # where good frames sit at 0.94 to 1.08. This judges against the median
        # of EVERY frame in the clip, which includes fast motion, so good
        # frames spread from 0.51 to 1.14. Same formula, wider population.
        #
        # Measured on side 0.1 the wider population still separates cleanly:
        # 34 of the 42 flagged frames are the camera being picked up at 27.2 to
        # 28.3 s, 7 are the first quarter second while it settles, and one is
        # the last frame. None is a fast-motion frame, which was the worry.
        record["degraded"] = bool(share < 0.5 or luma < 40.0)

    seconds = time.perf_counter() - started
    measured, sync = _sync_inputs(view, set_id)

    return {
        "schemaVersion": "video-keypoints-1",
        "source": {
            "videoFile": path.name,
            "videoSha256": sha256(path),
            "view": view,
            "setId": set_id,
            "decodedWidthPixels": width,
            "decodedHeightPixels": height,
            **stream,
            # Measured from the frame timestamps, not from equality with 30.0.
            # A camera locked at 25 or 60 fps is constant-rate and would read
            # False against a hardcoded 30.
            "constantFrameRate": constant_rate(stamps),
            "usableToSeconds": USABLE_TO.get((view, set_id)),
        },
        "model": {
            "tool": "mediapipe",
            "toolVersion": __import__("importlib.metadata", fromlist=["version"]).version("mediapipe"),
            "toolLicence": "Apache 2.0",
            "modelFile": MODEL.name,
            "modelSha256": sha256(MODEL).upper(),
            "modelSourceUrl": (
                "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
                "pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task"
            ),
            "modelFetchedUtc": "2026-08-28",
            "modelLicence": "Apache License, Version 2.0",
            "modelLicenceSource": MODEL_LICENCE_SOURCE,
            "landmarkNames": names,
            "landmarkEdges": landmark_edges(vision, names),
            "scope": MODEL_SCOPE,
        },
        "athlete": ATHLETE,
        "sync": _sync_block(view, set_id, measured, sync),
        "generatedFrom": {
            "commit": git_commit,
            "treeWasClean": tree_clean,
            "utcTimestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "secondsToExtract": round(seconds, 1),
        },
        "frames": records,
    }


def git_state() -> tuple[str, bool]:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                            text=True, cwd=SPIKE_DIR).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                           text=True, cwd=SPIKE_DIR).stdout.strip()
    return commit, not dirty


def restamp(path: Path) -> dict:
    """Rewrite one keypoint file's sync block, touching nothing else.

    EXTRACTION IS EXPENSIVE AND THE SYNC BLOCK IS NOT. Re-running MediaPipe over
    866 frames to correct a sentence would also re-derive every landmark, which
    changes the artefact far more than the fault being fixed. This reads the
    file, replaces the sync block from the same source the writer uses, and
    leaves every other key exactly as it was.
    """
    document = json.loads(path.read_text(encoding="utf-8"))
    source = document.get("source") or {}
    view = source.get("view")
    set_id = source.get("setId")
    if view is None or set_id is None:
        raise ValueError(f"{path.name} has no source.view / source.setId")
    before = document.get("sync")
    document["sync"] = _sync_block(view, set_id, *_sync_inputs(view, set_id))
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    return {"path": path, "before": before, "after": document["sync"]}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", choices=("front", "side"))
    parser.add_argument("--set", dest="set_id")
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--restamp", action="store_true",
        help="rewrite the sync block of every keypoint file already in "
             "poc-output, leaving all other keys untouched, and extract nothing")
    arguments = parser.parse_args(argv[1:])

    if arguments.restamp:
        files = sorted(OUTPUT.glob("keypoints-*.json"))
        if not files:
            print(f"no keypoint files in {OUTPUT}")
            return 0
        for path in files:
            found = restamp(path)
            was = (found["before"] or {}).get("method", "(none)")
            now = found["after"].get("method", "(none)")
            print(f"{path.name}" + "\n" + f"    was: {was}" + "\n" + f"    now: {now}  "
                  f"[{found['after'].get('methodKind')}]")
        return 0

    wanted = (
        [(v, s) for s in ("0.1", "0.2") for v in ("front", "side")]
        if arguments.all
        else [(arguments.view, arguments.set_id)]
    )
    if any(v is None or s is None for v, s in wanted):
        parser.error("give --view and --set, or --all")

    commit, clean = git_state()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for view, set_id in wanted:
        found = extract(view, set_id, commit, clean)
        where = OUTPUT / f"keypoints-{view}-{set_id}.json"
        where.write_text(json.dumps(found, indent=1) + "\n", encoding="utf-8")
        detected = sum(1 for f in found["frames"] if f["detected"])
        degraded = sum(1 for f in found["frames"] if f["degraded"])
        print(
            f"{view} {set_id}: {len(found['frames'])} frames, "
            f"{detected} with a pose, {degraded} degraded, "
            f"{found['generatedFrom']['secondsToExtract']} s  ->  {where.name}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
