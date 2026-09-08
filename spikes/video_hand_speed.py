"""How fast her hand is moving when she lets the ball go.

Marius watched the coach player on 2026-09-08 and said the athlete flicks her
wrist and fingers in the last moments of contact, and the engine's release has
none. The movement lane models that release hand against the numbers here, so
this module exists rather than a scratch script: a band another lane cites is
a band whose instrument is committed beside it.

WHAT THIS MEASURES, AND WHAT IT REFUSES TO.

  measured   the speed of the hand and of the wrist through a release, on two
             scales that share no arithmetic
  REFUSED    the forearm-to-hand ANGLE. The hand is about twenty pixels across
             in this footage, so one pixel of landmark error is 2.0 to 3.3
             degrees, and a still, well-tracked arm reads 11 to 22 degrees of
             swing. There is no degrees column in this module and that is the
             finding, not an omission.

THE RELEASE FRAMES ARE READ ON THE PICTURES, NOT DERIVED HERE. The rule is:
the release is the FIRST FRAME IN WHICH THE BALL LEAVES THE HANDS, read at a
step of one frame at 400 px. `RELEASES` records what was read, with the ones
where the ball is blurred at separation marked `soft`. Nothing in this file
finds a release; a wrist-speed peak was used to narrow where to look, and it
fires on catches too.

THE CONVENTION MATTERS BECAUSE THE BALL SEPARATES DURING AN EXPOSURE. At the
release frame the ball is a smear whose trailing edge still touches the
fingertips; the frame after is the first with a gap clear of the smear. This
module reads the smear as the ball, so the release is the frame in which the
ball leaves the hands rather than the first frame with clear air behind it. An
independent review of 2026-09-08 read the same five frames one later under the
other convention. The band does not move either way, the `at` column does.

EVERY ARTEFACT IS PINNED BY SHA256, NEVER BY NAME. The two side recordings
swapped names at source on 2026-09-07, and their keypoint files record it in
`source.renamedFrom`. `load` refuses unless the file's own hash and the
`videoSha256` it carries are the ones recorded in `EXPECTED`, so a rename
cannot quietly change which recording produced the band. If a recording is
extracted again, its hash changes and this module refuses until the new hash
is recorded and BAND.md is regenerated, which is the intended behaviour: the
band belongs to the bytes it was measured on.

TWO SCALES, AND NEITHER IS PREFERRED.

  image   pixels per frame, converted by HER OWN height in the picture: nose
          to heel, against 1.77 m standing times 0.935
  world   the model's own metric landmarks, straight out of the file

They are printed side by side because two instruments that fail differently
are the only check available here. They disagree by about 20 per cent, and the
band quoted to another lane spans both.

ONE WORD, TWO ARMS, TWO QUANTITIES. The athlete's arm belongs to the footage
and is READ from each keypoint file. The engine's clips are in the ENGINE's arm
lengths, and converting those with the athlete's arm inflates every engine
metre by 1.46. The engine's arm is read from the engine's own receipt at run
time. Neither number is typed into an arithmetic path here: the constants below
are the values the files carried on 2026-09-08, and `load` refuses if a file
disagrees with them.

    pixi run --frozen python -B video_hand_speed.py
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import NamedTuple

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

KEYPOINTS = SPIKE_DIR / "poc-output" / "video"
LIBRARY = SPIKE_DIR / "poc-output" / "poc-output" / "library"
BAND_DOC = SPIKE_DIR / "video-annotations" / "hand-speed" / "BAND.md"

# Her height, and the nose-to-heel fraction of stature used to turn a pixel
# span into metres. Marius supplied the height on 2026-08-28.
ATHLETE_HEIGHT_METRES = 1.77
NOSE_TO_HEEL_FRACTION = 0.935
ATHLETE_ARM_METRES = 0.77

# The window either side of a release, in frames.
BEFORE, AFTER = 10, 5

# The null search ignores frames where the near wrist is barely tracked. An
# untracked wrist sits still, so without this the quietest window in a
# recording would be the one the model had most trouble seeing.
NULL_MIN_VISIBILITY = 0.7

# The near arm. In BOTH runs the side camera sees her left arm nearer: the
# left wrist tracks at 0.86 and 0.69 visibility against 0.31 and 0.18 for the
# right, which is the occluded one.
#
# THIS IS A DEFAULT THAT `band_rows` CHECKS AT EVERY RELEASE, not a fact about
# the next recording. It was advice until 2026-09-08: `check_near_arm` existed
# and only a test ever called it, so a recording shot from the other side would
# have been measured on the occluded arm without complaint.
NEAR_ARM = "left"


class Release(NamedTuple):
    """One release, as READ ON THE PICTURES at a step of one."""

    view: str
    setId: str
    frame: int
    reading: str        # "crisp", or "soft" where the ball blurs at separation


RELEASES = (
    Release("side", "0.2", 254, "crisp"),
    Release("side", "0.2", 306, "crisp"),
    Release("side", "0.2", 366, "crisp"),
    Release("side", "0.2", 423, "crisp"),
    Release("side", "0.2", 475, "soft"),
    Release("side", "0.2", 525, "soft"),
    Release("side", "0.2", 593, "crisp"),
    Release("side", "0.2", 646, "crisp"),
    Release("side", "0.2", 700, "crisp"),
    Release("side", "0.1", 285, "crisp"),
    Release("side", "0.1", 340, "crisp"),
    Release("side", "0.1", 615, "crisp"),
)

# NINE RELEASES IN RUN 2, NOT TEN. She catches ten times; the tenth possession
# has no release. Read at a step of one over side 763..794 she holds the ball
# for 32 frames and walks out of the drill with it, which is what the event
# ledger says in words: "after 29.5 s she walks to the camera holding it".
# Side 794 is front 872, 29.07 s.
NO_RELEASE = {("side", "0.2"): (739, "she carries the ball out of the drill")}

# THE REPETITION WITH THE LONG HOLD. She keeps the ball about a second before
# throwing it and the throw is slower. It is measured like the rest and left
# out of the band, by name rather than by a threshold.
HELD_REPETITION = ("side", "0.2", 593)


class Artefact(NamedTuple):
    """What a recording must hash to before this module will measure it."""

    keypointsSha256: str
    videoSha256: str


# PINNED 2026-09-08 by hashing the files this band was measured on. The two
# side recordings carry the same four filenames they were renamed to at source
# on 2026-09-07; only these hashes say which recording is which.
EXPECTED = {
    ("side", "0.1"): Artefact(
        "61a8940128ebf12ce00d432391fcba18164b3dce2ce813126ad79f153f9fd333",
        "6e8f9fb2fe03f517a595a202ffb69e1554c228a5931919a3da359e6a590f2912"),
    ("side", "0.2"): Artefact(
        "f98e5dc50f4a749f85bc6411c7ec1b0ff364c4fd35a131ac9ddc0e4cffb79a62",
        "253fa551605e4844dcf509b4462464b97043a55b5e059e6221b73723353caf66"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def keypoint_path(view: str, set_id: str) -> Path:
    return KEYPOINTS / f"keypoints-{view}-{set_id}.json"


def load(view: str, set_id: str) -> tuple[dict, dict[str, int]]:
    """Read a recording's keypoints, REFUSING anything but the exact bytes.

    Three things are checked and each can fail on its own: the file hashes to
    what was recorded, it describes the recording that was recorded, and it
    carries the athlete figures this module was calibrated against.
    """
    path = keypoint_path(view, set_id)
    if not path.exists():
        raise SystemExit(
            f"{path.name} is not on this machine. The keypoint artefacts are "
            "not in git; extract them before running this.")
    expected = EXPECTED.get((view, set_id))
    if expected is None:
        raise SystemExit(
            f"no hash is recorded for {view} {set_id}; this module measures "
            "only recordings pinned in EXPECTED.")
    found = sha256(path)
    if found != expected.keypointsSha256:
        raise SystemExit(
            f"{path.name} hashes to {found[:12]} and {view} {set_id} is "
            f"pinned to {expected.keypointsSha256[:12]}. The file is not the "
            "one this band was measured on; the side recordings have been "
            "renamed at source once already.")
    d = json.loads(path.read_text(encoding="utf-8"))
    carried = d["source"]["videoSha256"]
    if carried != expected.videoSha256:
        raise SystemExit(
            f"{path.name} describes video {carried[:12]} and {view} {set_id} "
            f"is pinned to {expected.videoSha256[:12]}.")
    athlete = d.get("athlete") or {}
    for field, value in (("heightMetres", ATHLETE_HEIGHT_METRES),
                         ("oneArmReachMetres", ATHLETE_ARM_METRES)):
        if field not in athlete:
            raise SystemExit(
                f"{path.name} carries no athlete.{field}; this module reads "
                "the athlete's figures rather than typing them.")
        if abs(athlete[field] - value) > 1e-9:
            raise SystemExit(
                f"{path.name} says athlete.{field} is {athlete[field]} and "
                f"this module was calibrated on {value}.")
    return d, {n: i for i, n in enumerate(d["model"]["landmarkNames"])}


def provenance(view: str, set_id: str) -> dict:
    """What a reader needs to check the band against: every input, hashed."""
    d, _ = load(view, set_id)
    return {
        "view": view,
        "setId": set_id,
        "keypointsSha256": sha256(keypoint_path(view, set_id)),
        "videoSha256": d["source"]["videoSha256"],
        "modelSha256": d["model"]["modelSha256"],
        "modelFile": d["model"]["modelFile"],
        "framesPerSecondMeasured": d["source"]["framesPerSecondMeasured"],
        "frames": len(d["frames"]),
    }


def image_point(frame: dict, index: dict, name: str) -> tuple[float, float]:
    lm = frame["landmarks"][index[name]]
    return lm["xPixel"], lm["yPixel"]


def world_point(frame: dict, index: dict, name: str) -> tuple[float, float, float]:
    lm = frame["worldLandmarks"][index[name]]
    return lm["xWorldMetres"], lm["yWorldMetres"], lm["zWorldMetres"]


def visibility(frame: dict, index: dict, name: str) -> float:
    return frame["landmarks"][index[name]]["visibility"]


def hand_centre(frame: dict, index: dict, getter, side: str = NEAR_ARM):
    a = getter(frame, index, f"{side}_index")
    b = getter(frame, index, f"{side}_pinky")
    return tuple((u + v) / 2 for u, v in zip(a, b))


def check_near_arm(d: dict, index: dict, centre: int) -> str:
    """Which arm the camera actually sees, MEASURED not assumed.

    A side view occludes one arm behind the other. Taking the wrong one would
    give the speed of a landmark the model is guessing at, and the guess is
    smooth, so it would look like a clean slow trace rather than an error.
    """
    seen = {"left": 0.0, "right": 0.0}
    counted = 0
    for n in range(max(1, centre - BEFORE), centre + AFTER + 1):
        if n >= len(d["frames"]):
            break
        frame = d["frames"][n]
        if not frame["detected"]:
            continue
        for side in seen:
            seen[side] += visibility(frame, index, f"{side}_wrist")
        counted += 1
    if not counted:
        raise SystemExit(f"no detected frames around {centre}")
    return max(seen, key=lambda side: seen[side])


def gate_near_arm(d: dict, index: dict, centre: int,
                  side: str = NEAR_ARM) -> None:
    """REFUSE if the camera does not see the arm we are about to measure.

    The failure this prevents is silent. An occluded wrist is not missing: the
    model reports it, smoothly, as a guess, so measuring the far arm returns a
    clean slow trace that looks like a result.
    """
    seen = check_near_arm(d, index, centre)
    if seen != side:
        source = d["source"]
        raise SystemExit(
            f"{source['view']} {source['setId']} frame {centre}: the camera "
            f"sees the {seen} arm nearer, but the measurement asks for the "
            f"{side} one. Set NEAR_ARM, or pass side= for this recording.")


def athlete_height(d: dict) -> float:
    """Her height, READ from the recording rather than typed here."""
    return d["athlete"]["heightMetres"]


def metres_per_pixel(frame: dict, index: dict,
                     height_metres: float) -> float | None:
    """A scale from HER OWN height in this frame, so it follows her about."""
    nose = image_point(frame, index, "nose")[1]
    heel = max(image_point(frame, index, "left_heel")[1],
               image_point(frame, index, "right_heel")[1])
    span = heel - nose
    if span <= 0:
        return None
    return (height_metres * NOSE_TO_HEEL_FRACTION) / span


def speed_rows(d: dict, index: dict, centre: int,
               side: str = NEAR_ARM) -> list[dict]:
    """Hand and wrist speed, frame by frame, on both scales."""
    fps = d["source"]["framesPerSecondMeasured"]
    rows = []
    for n in range(centre - BEFORE, centre + AFTER + 1):
        if n < 1 or n >= len(d["frames"]):
            continue
        here, was = d["frames"][n], d["frames"][n - 1]
        row = {"frame": n, "offset": n - centre,
               "quality": here["frame_quality"],
               "degraded": here["degraded"],
               "visibilityWrist": visibility(here, index, f"{side}_wrist")}
        if not (here["detected"] and was["detected"]):
            row["handImage"] = row["handWorld"] = None
            row["wristImage"] = row["wristWorld"] = None
            rows.append(row)
            continue
        scale = metres_per_pixel(here, index, athlete_height(d))
        for part in ("hand", "wrist"):
            if part == "hand":
                now2 = hand_centre(here, index, image_point)
                was2 = hand_centre(was, index, image_point)
                now3 = hand_centre(here, index, world_point)
                was3 = hand_centre(was, index, world_point)
            else:
                now2 = image_point(here, index, f"{side}_wrist")
                was2 = image_point(was, index, f"{side}_wrist")
                now3 = world_point(here, index, f"{side}_wrist")
                was3 = world_point(was, index, f"{side}_wrist")
            row[f"{part}Image"] = (math.dist(now2, was2) * scale * fps
                                   if scale else None)
            # The model card calls the Z up to scale and not metric, so the
            # world speed is taken in the two metric axes only.
            row[f"{part}World"] = math.dist(now3[:2], was3[:2]) * fps
        rows.append(row)
    return rows


def search_null(d: dict, index: dict, side: str = NEAR_ARM) -> dict:
    """The stillest window in a recording, FOUND rather than chosen.

    A null picked by eye can be wrong in the direction that flatters the
    result, and mine was: the first stretch I believed was a stand held a
    3.03 m/s frame, which would have put the floor forty times too high. This
    searches every window of the same length the release traces use and
    returns the quietest, so the floor is the recording's own.
    """
    fps = d["source"]["framesPerSecondMeasured"]
    length = BEFORE + AFTER + 1
    speed: dict[int, float] = {}
    for n in range(1, len(d["frames"])):
        here, was = d["frames"][n], d["frames"][n - 1]
        if not (here["detected"] and was["detected"]) or here["degraded"]:
            continue
        if visibility(here, index, f"{side}_wrist") < NULL_MIN_VISIBILITY:
            continue
        scale = metres_per_pixel(here, index, athlete_height(d))
        if scale is None:
            continue
        speed[n] = math.dist(hand_centre(here, index, image_point),
                             hand_centre(was, index, image_point)) * scale * fps
    best = None
    for start in range(1, len(d["frames"]) - length):
        window = [speed.get(n) for n in range(start, start + length)]
        if any(v is None for v in window):
            continue
        peak = max(window)
        if best is None or peak < best["peak"]:
            best = {"start": start, "centre": start + BEFORE, "peak": peak,
                    "mean": sum(window) / len(window)}
    if best is None:
        raise SystemExit("no window of this length is fully tracked")
    return best


def engine_arm_metres() -> tuple[float, Path]:
    """The ENGINE's arm, read from the engine's own receipt.

    `read_ball` in clip_geometry.py normalises the ball's offset by
    `norm(elbow - l_uparm) + norm(l_wrist - elbow)` on the SOLVED joints, so a
    clip's "arm lengths" are the engine's arm and not the athlete's. Reading
    the figure rather than typing it is the point: an earlier version of this
    work spent `ATHLETE_ARM_METRES` on the engine's unit and inflated every
    engine metre by 1.46.
    """
    receipt = LIBRARY / "netball_two_hand_snatch_pull_in.reach.json"
    if not receipt.exists():
        raise SystemExit(
            f"{receipt.name} is not on this machine; it carries the engine's "
            "own armLengthCm and this module will not type one in.")
    return json.loads(receipt.read_text(encoding="utf-8"))["armLengthCm"] / 100.0, receipt


def band_rows() -> list[dict]:
    """One row per release: the peak in the window, on both scales."""
    rows = []
    loaded: dict[tuple[str, str], tuple[dict, dict]] = {}
    nulls: dict[tuple[str, str], dict] = {}
    for release in RELEASES:
        key = (release.view, release.setId)
        if key not in loaded:
            loaded[key] = load(*key)
            nulls[key] = search_null(*loaded[key])
        d, index = loaded[key]
        gate_near_arm(d, index, release.frame)
        measured = [r for r in speed_rows(d, index, release.frame)
                    if r["handImage"] is not None]
        best_image = max(measured, key=lambda r: r["handImage"])
        best_world = max(measured, key=lambda r: r["handWorld"])
        rows.append({
            "setId": release.setId,
            "frame": release.frame,
            "reading": release.reading,
            "handImage": best_image["handImage"],
            "atImage": best_image["offset"],
            "handWorld": best_world["handWorld"],
            "atWorld": best_world["offset"],
            "nullImage": nulls[key]["peak"],
            "inBand": (release.view, release.setId, release.frame)
                      != HELD_REPETITION and release.reading == "crisp",
        })
    return rows


def band(rows: list[dict] | None = None) -> tuple[float, float]:
    """The range another lane should quote: across BOTH scales, crisp only.

    The held repetition is excluded by name, not by a threshold: she keeps the
    ball about a second there and throws it more slowly, which is a different
    movement rather than an outlier.
    """
    rows = band_rows() if rows is None else rows
    wanted = [r for r in rows if r["inBand"]]
    if not wanted:
        raise SystemExit("no crisp releases outside the held repetition")
    return (min(min(r["handImage"], r["handWorld"]) for r in wanted),
            max(max(r["handImage"], r["handWorld"]) for r in wanted))


def recordings() -> tuple[tuple[str, str], ...]:
    """The recordings the band is measured on, in the order they are used."""
    seen = []
    for release in RELEASES:
        if (release.view, release.setId) not in seen:
            seen.append((release.view, release.setId))
    return tuple(seen)


def provenance_rows() -> list[dict]:
    return [provenance(*key) for key in recordings()]


def main(argv: list[str]) -> int:
    print("THE INPUTS, hashed. A band without them cannot be checked.")
    for p in provenance_rows():
        print(f"  {p['view']} {p['setId']}: keypoints "
              f"{p['keypointsSha256'][:12]}, video {p['videoSha256'][:12]}, "
              f"model {p['modelSha256'][:12]}, "
              f"{p['framesPerSecondMeasured']} fps, {p['frames']} frames")
    print()
    rows = band_rows()
    low, high = band(rows)
    print(f"{'run':>5s} {'release':>8s} {'read':>6s} {'hand img':>9s} "
          f"{'at':>4s} {'hand wld':>9s} {'at':>4s} {'null img':>9s}")
    for r in rows:
        print(f"{r['setId']:>5s} {r['frame']:8d} {r['reading']:>6s} "
              f"{r['handImage']:9.2f} {r['atImage']:+4d} "
              f"{r['handWorld']:9.2f} {r['atWorld']:+4d} "
              f"{r['nullImage']:9.2f}")
    print()
    print(f"THE BAND, across both scales, crisp releases outside the held "
          f"repetition: {low:.1f} to {high:.1f} m/s")
    arm, receipt = engine_arm_metres()
    print(f"the engine's arm is {arm:.4f} m, read from {receipt.name} "
          "(field armLengthCm)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
