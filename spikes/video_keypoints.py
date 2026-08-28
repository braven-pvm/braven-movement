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
SYNC = {
    "0.1": {"offsetSecondsToReference": 1.0, "thisViewSeconds": 8.25,
            "referenceViewSeconds": 9.25},
}
SYNC_UNCERTAINTY_SECONDS = 0.15
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


def _sync_block(view: str, set_id: str, measured: bool, sync: dict) -> dict:
    """The sync block, or an honest statement that there is not one.

    A set nobody has measured must NOT carry a null offset beside a `worked`
    example of nulls. The schema tells a consumer to assert
    `thisViewSeconds + offsetSecondsToReference == referenceViewSeconds` on
    load, and that assertion on None is a crash rather than a check.
    """
    block = {
        "referenceView": REFERENCE_VIEW,
        "measured": measured,
        "offsetSecondsToReference": sync.get("offsetSecondsToReference"),
    }
    if not measured:
        block["note"] = (
            f"No offset has been measured for set {set_id}. Only set 0.1 has "
            "two matched events. Do not pair these views on a clock until one "
            "is measured; the reference view's own zero is a definition, not a "
            "measurement of this pair."
        )
        return block
    block["offsetUncertaintySeconds"] = SYNC_UNCERTAINTY_SECONDS
    block["method"] = "two visual events matched by eye; no clap exists in this material"
    block["worked"] = {
        "event": "first catch, seen in both views",
        "thisViewSeconds": sync.get("thisViewSeconds"),
        "referenceViewSeconds": sync.get("referenceViewSeconds"),
    }
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
    # A set whose offset nobody has measured says so, rather than carrying
    # nulls that would break the assertion the schema tells consumers to run.
    measured = set_id in SYNC
    sync = dict(SYNC.get(set_id, {}))
    if view == REFERENCE_VIEW:
        # The reference view's offset is zero by definition, measured or not.
        sync["offsetSecondsToReference"] = 0.0
        if measured:
            sync["thisViewSeconds"] = sync.get("referenceViewSeconds")

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
            "constantFrameRate": abs((stream["framesPerSecondMeasured"] or 0) - 30.0) < 1e-6,
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


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", choices=("front", "side"))
    parser.add_argument("--set", dest="set_id")
    parser.add_argument("--all", action="store_true")
    arguments = parser.parse_args(argv[1:])

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
