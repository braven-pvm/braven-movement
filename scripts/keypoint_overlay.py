"""Draw the movement lane's keypoints over the video they were read from.

Marius grades by eye. This is how his eye reaches the data: the skeleton on
the athlete, in both views, at one instant of wall clock time. If the solve has
put an elbow in the wrong place, a person sees it here in a second and no
number in a receipt says it as fast.

It draws and it does not solve. Every position comes from the keypoint file.
Nothing here moves a joint to make a picture look better, because a picture
corrected in the renderer hides the fault it was drawn to show.

WHAT IT REFUSES TO GUESS

The skeleton EDGES come from the keypoint file. Without them a viewer must
invent a topology, and an invented one draws a confident limb through a chest
the day the model changes. If the file carries none, this refuses, unless a
person passes `--assume-topology`, and then the assumption is STAMPED ON THE
PICTURE so nobody mistakes it for something that was read.

THE TWO CLOCKS

Each keypoint file carries `sync.offsetSecondsToReference`: the number you add
to a timestamp IN THAT FILE to reach the reference view's clock. This tool asks
for a time on the reference clock and converts, so a caller never does the
arithmetic. Where the file carries a worked example, the conversion is asserted
against it on load rather than trusted.

    python keypoint_overlay.py --keypoints front.json --keypoints side.json \
        --at 9.25 --out overlay.png
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from video_sync_sheet import (  # noqa: E402
    Image,
    ImageDraw,
    degraded,
    frame_quality,
    load_font,
    nearest_frame,
    require_imaging,
)

JOINT_RADIUS = 4
SEEN = 0.5          # visibility at or above this is drawn solid
GLIMPSED = 0.2      # below this a landmark is not drawn at all


def read_keypoints(path: Path) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    check_sync_direction(document, path)
    return document


def check_sync_direction(document: dict, path: Path) -> None:
    """Assert the offset's DIRECTION against the file's own worked example.

    The two lanes define their offsets in opposite directions, on purpose and
    each unambiguous alone. Prose about which way it runs is what failed the
    first time this was written down, so where the file carries real numbers
    they are checked rather than read.
    """
    sync = document.get("sync") or {}
    worked = sync.get("worked")
    if not worked:
        return
    offset = float(sync.get("offsetSecondsToReference", 0.0))
    here = float(worked["thisViewSeconds"])
    there = float(worked["referenceViewSeconds"])
    if abs((here + offset) - there) > 0.001:
        raise SystemExit(
            f"{path.name}: the sync offset does not agree with the file's own "
            f"worked example. {here} + {offset} is {here + offset}, and the "
            f"example says the reference clock reads {there}. One of the two "
            "is wrong, and a viewer must not pick."
        )


def reference_to_local(document: dict, reference_seconds: float) -> float:
    """A time on the reference view's clock, expressed in this file's clock."""
    sync = document.get("sync") or {}
    if (sync.get("referenceView") or "") == (document["source"].get("view") or ""):
        return reference_seconds
    return reference_seconds - float(sync.get("offsetSecondsToReference", 0.0))


def frame_nearest(document: dict, local_seconds: float) -> dict | None:
    frames = [frame for frame in document.get("frames", []) if frame.get("detected")]
    if not frames:
        return None
    return min(frames, key=lambda frame: abs(frame["ptsSeconds"] - local_seconds))


SAMPLES = Path("F:/Repositories/braven-movement/.assets/video-samples/session-1.0")


def find_video(named: str, root: Path | None) -> Path:
    """Resolve the keypoint file's `videoFile` to something on this machine.

    The schema records a BARE FILENAME, "side 0.1.mp4", which is right: the
    keypoint file describes a recording and not a directory on whoever's disk
    wrote it. So a reader must resolve it, and this one looks in the directory
    given, then beside the sample material, then as an outright path.

    Found by reading the schema again rather than by waiting for the first real
    file to be refused.
    """
    candidates = []
    if root is not None:
        candidates.append(root / named)
    candidates.append(SAMPLES / named)
    candidates.append(Path(named))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    looked = ", ".join(str(candidate) for candidate in candidates)
    raise SystemExit(
        f"the keypoint file names the recording {named!r}, and it is not on "
        f"this machine. Looked in: {looked}. Pass --video-root."
    )


def edges_for(document: dict, assumed: list[tuple[str, str]] | None):
    """The skeleton's connections, from the file or refused."""
    model = document.get("model") or {}
    named = model.get("landmarkEdges")
    if named:
        return [tuple(edge) for edge in named], False
    if assumed is not None:
        return assumed, True
    raise SystemExit(
        f"{document['source'].get('videoFile', 'the keypoint file')} carries no "
        "landmarkEdges, so the skeleton's shape is not in the data. Add the "
        "edges to the file, or pass --assume-topology to draw a guessed one, "
        "which is then stamped on the picture as guessed."
    )


def draw_skeleton(
    image,
    frame: dict,
    edges,
    scale_x: float,
    scale_y: float,
    colour=(90, 200, 255),
) -> dict:
    """Draw one frame's landmarks. Returns what it drew and what it skipped."""
    canvas = ImageDraw.Draw(image, "RGBA")
    points = {
        landmark["name"]: landmark
        for landmark in frame.get("landmarks", [])
    }

    def place(landmark):
        return (landmark["xPixel"] * scale_x, landmark["yPixel"] * scale_y)

    drawn_edges, missing_edges = 0, []
    for first, second in edges:
        a, b = points.get(first), points.get(second)
        if a is None or b is None:
            missing_edges.append((first, second))
            continue
        seen = min(a.get("visibility", 1.0), b.get("visibility", 1.0))
        if seen < GLIMPSED:
            continue
        # A barely seen joint is drawn faintly rather than confidently or not
        # at all: the reader must be able to tell a measured limb from a
        # guessed one without reading the receipt.
        alpha = 235 if seen >= SEEN else 90
        canvas.line([place(a), place(b)], fill=colour + (alpha,), width=3)
        drawn_edges += 1

    faint = 0
    for landmark in points.values():
        seen = landmark.get("visibility", 1.0)
        if seen < GLIMPSED:
            continue
        x, y = place(landmark)
        if seen < SEEN:
            faint += 1
        fill = (255, 220, 90, 235) if seen >= SEEN else (255, 220, 90, 90)
        canvas.ellipse(
            [x - JOINT_RADIUS, y - JOINT_RADIUS, x + JOINT_RADIUS, y + JOINT_RADIUS],
            fill=fill,
        )

    return {
        "landmarks": len(points),
        "edgesDrawn": drawn_edges,
        "edgesMissingLandmarks": len(missing_edges),
        "faintLandmarks": faint,
        "hidden": sum(
            1 for item in points.values() if item.get("visibility", 1.0) < GLIMPSED
        ),
    }


def build_overlay(
    documents: list[dict],
    reference_seconds: float,
    out: Path,
    *,
    assumed_topology=None,
    height: int = 640,
    video_root: Path | None = None,
) -> dict:
    require_imaging()
    work = Path(tempfile.mkdtemp(prefix="overlay_"))
    label = load_font(15)
    head = load_font(19)
    panels, report = [], []

    for document in documents:
        source = document["source"]
        video = find_video(source["videoFile"], video_root)

        local = reference_to_local(document, reference_seconds)
        frame = frame_nearest(document, local)
        if frame is None:
            raise SystemExit(
                f"{video.name} has no detected frame near {local:.3f}s. An "
                "undetected frame carries no landmarks, and an overlay of "
                "nothing is not a picture of a fault."
            )

        image_path, shown_at = nearest_frame(video, frame["ptsSeconds"], work,
                                             source.get("view", "view"))
        picture = Image.open(image_path).convert("RGB")
        quality = frame_quality(image_path)
        edges, guessed = edges_for(document, assumed_topology)

        # The keypoints are in DECODED pixels. Anything drawn on a resized
        # picture must be scaled by the same factor, or every joint sits a few
        # percent from the limb it belongs to and the error looks like a solve.
        scale_x = picture.width / float(source["decodedWidthPixels"])
        scale_y = picture.height / float(source["decodedHeightPixels"])
        counts = draw_skeleton(picture, frame, edges, scale_x, scale_y)

        width = max(1, round(picture.width * height / picture.height))
        panels.append((source.get("view", "view"), picture.resize((width, height),
                                                                  Image.LANCZOS),
                       frame, shown_at, quality, guessed, counts))
        report.append({
            "view": source.get("view"),
            "videoFile": str(video),
            "askedReferenceSeconds": round(reference_seconds, 4),
            "askedLocalSeconds": round(local, 4),
            "keypointFrameSeconds": round(frame["ptsSeconds"], 4),
            "videoFrameSeconds": round(shown_at, 4),
            "keypointToVideoMs": round(
                (shown_at - frame["ptsSeconds"]) * 1000.0, 2
            ),
            "landmarksFrom": (document.get("model") or {}).get("tool"),
            "topologyGuessed": guessed,
            **counts,
        })

    gap, strip, pad, header = 10, 54, 14, 78
    total = sum(panel[1].width for panel in panels) + gap * (len(panels) - 1)
    title = (f"keypoints over the video, at {reference_seconds:.3f} s "
             "on the reference clock")
    tools = sorted({
        (document.get("model") or {}).get("tool", "unnamed")
        for document in documents
    })
    legend = ("solid joint seen, faint joint barely seen, absent not seen.")
    # A single portrait panel is narrower than the header, and a clipped
    # header is a caption that stops mid-sentence on the one artefact a
    # person is asked to trust. Size the sheet to whichever is wider.
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    widest_text = max(
        measure.textbbox((0, 0), title, font=head)[2],
        measure.textbbox((0, 0), f"landmarks from: {', '.join(tools)}", font=label)[2],
        measure.textbbox((0, 0), legend, font=label)[2],
    )
    sheet = Image.new(
        "RGB",
        (pad * 2 + max(total, widest_text), header + pad + height + strip),
        (24, 24, 27),
    )
    canvas = ImageDraw.Draw(sheet)
    canvas.text((pad, 10), title, font=head, fill=(240, 240, 245))
    # WHERE THE NUMBERS CAME FROM, on the picture. A viewer cannot tell a real
    # solve from a placeholder by looking at a skeleton, and a picture that
    # does not say what produced it will eventually be read as a result.
    canvas.text((pad, 36), f"landmarks from: {', '.join(tools)}",
                font=label, fill=(255, 200, 120))
    canvas.text((pad, 54), legend, font=label, fill=(170, 170, 180))

    x = pad
    for view, picture, frame, shown_at, quality, guessed, counts in panels:
        sheet.paste(picture, (x, header + pad))
        canvas.text((x, header + pad + height + 4),
                    f"{view}   video {shown_at:.3f} s   keypoints "
                    f"{frame['ptsSeconds']:.3f} s", font=label, fill=(235, 235, 240))
        canvas.text((x, header + pad + height + 22),
                    f"{counts['edgesDrawn']} bones, {counts['faintLandmarks']} faint, "
                    f"{counts['hidden']} unseen", font=label, fill=(150, 190, 150))
        if guessed:
            canvas.rectangle([x, header + pad, x + 330, header + pad + 22],
                             fill=(150, 40, 30))
            canvas.text((x + 5, header + pad + 3),
                        "SKELETON SHAPE GUESSED, not read from the file",
                        font=label, fill=(255, 235, 230))
        x += picture.width + gap

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return {"overlay": str(out), "referenceSeconds": reference_seconds,
            "views": report}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keypoints", action="append", required=True, type=Path,
                        help="one keypoint file per view, repeatable")
    parser.add_argument("--at", type=float, required=True,
                        help="seconds on the REFERENCE view's clock")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--height", type=int, default=640)
    parser.add_argument("--video-root", type=Path, default=None,
                        help="where the recordings named in the keypoint files "
                             "live on this machine")
    parser.add_argument("--assume-topology", type=Path, default=None,
                        help="a JSON list of [from, to] name pairs, used only "
                             "when the keypoint file carries no landmarkEdges. "
                             "The picture is stamped as guessed.")
    arguments = parser.parse_args(argv)

    assumed = None
    if arguments.assume_topology:
        assumed = [
            tuple(edge)
            for edge in json.loads(
                arguments.assume_topology.read_text(encoding="utf-8")
            )
        ]

    documents = [read_keypoints(path) for path in arguments.keypoints]
    receipt = build_overlay(documents, arguments.at, arguments.out,
                            assumed_topology=assumed, height=arguments.height,
                            video_root=arguments.video_root)
    arguments.out.with_suffix(".json").write_text(
        json.dumps(receipt, indent=2), encoding="utf-8"
    )

    worst = max(abs(view["keypointToVideoMs"]) for view in receipt["views"])
    print(f"{arguments.out}  {len(receipt['views'])} views  "
          f"worst keypoint-to-video gap {worst:.1f} ms")
    if any(view["topologyGuessed"] for view in receipt["views"]):
        print("the skeleton's shape was GUESSED. Add landmarkEdges to the "
              "keypoint file and draw it again.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
