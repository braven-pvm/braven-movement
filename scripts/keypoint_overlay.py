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
import hashlib
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
    # The hash of the file ACTUALLY READ, carried into the receipt. A relayed
    # constant from someone's report goes stale the moment the producer
    # regenerates, which happened within an hour of this being written; a
    # reader compares this against whatever report they hold.
    document["_readFrom"] = {"path": str(path), "sha256": sha256_of(path)}
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
    offset = sync_offset(document)
    if not worked or offset is None:
        # Nothing stated is not something to check. A file that says it has no
        # measured offset must LOAD, so a single view can still be drawn.
        return
    here = float(worked["thisViewSeconds"])
    there = float(worked["referenceViewSeconds"])
    if abs((here + offset) - there) > 0.001:
        raise SystemExit(
            f"{path.name}: the sync offset does not agree with the file's own "
            f"worked example. {here} + {offset} is {here + offset}, and the "
            f"example says the reference clock reads {there}. One of the two "
            "is wrong, and a viewer must not pick."
        )


def is_reference_view(document: dict) -> bool:
    sync = document.get("sync") or {}
    return (sync.get("referenceView") or "") == (document["source"].get("view") or "")


def sync_offset(document: dict) -> float | None:
    """The measured offset to the reference clock, or None when there is none.

    `measured: false` and a null offset both mean the same thing: nobody has
    measured how these two cameras line up. Set 0.2 carries exactly that,
    because only set 0.1 has two matched events.

    A DEFAULT OF ZERO IS A CLAIM, not a fallback. It says the cameras started
    together, which for set 0.2 is unknown and for these files is false. A
    first version of this used `sync.get(..., 0.0)` and ignored `measured`
    entirely, so it would have paired two unsynchronised views into a picture
    that looks matched. It happened not to, only because the movement lane
    wrote `null` and the arithmetic threw. Their defensiveness covered for this
    function; nothing here did.
    """
    sync = document.get("sync") or {}
    if sync.get("measured") is False:
        return None
    value = sync.get("offsetSecondsToReference")
    return None if value is None else float(value)


def reference_to_local(document: dict, reference_seconds: float) -> float:
    """A time on the reference view's clock, expressed in this file's clock."""
    if is_reference_view(document):
        return reference_seconds
    offset = sync_offset(document)
    if offset is None:
        view = document["source"].get("view", "this view")
        raise SystemExit(
            f"{view} carries no measured offset to the reference clock, so a "
            "time on that clock cannot be placed in this file. Draw it alone "
            "with --local, which reads --at as this view's OWN time and says "
            "so on the picture, or wait for the offset to be measured. Do not "
            "pair views that have never been lined up."
        )
    return reference_seconds - offset


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


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_video(video: Path, claimed: str | None) -> dict:
    """Is this the recording the keypoints were actually read from?

    The overlay PRINTS the model that produced the landmarks, which is a claim
    about provenance it was not checking. Drawing a skeleton over a different
    recording of the same drill produces a picture that is entirely wrong and
    entirely plausible: a body, a skeleton, and no relation between them.

    A mismatch REFUSES rather than stamps. There is no honest picture of
    keypoints drawn on a recording they did not come from, so there is nothing
    for a warning label to make acceptable.

    No claim in the file is reported as unverified, never as verified. Absence
    of a check is not a passing check.
    """
    if not claimed:
        return {"claimed": None, "actual": None, "verified": None}
    actual = sha256_of(video)
    if actual != claimed:
        raise SystemExit(
            f"{video.name} is NOT the recording these keypoints were read "
            f"from. The keypoint file names sha256 {claimed[:16]}... and the "
            f"file on this machine is {actual[:16]}.... Drawing one on the other "
            "would produce a picture with no relation between the body and the "
            "skeleton."
        )
    return {"claimed": claimed, "actual": actual, "verified": True}


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
    local_clock: bool = False,
) -> dict:
    require_imaging()
    work = Path(tempfile.mkdtemp(prefix="overlay_"))
    label = load_font(15)
    head = load_font(19)
    panels, report = [], []

    for document in documents:
        source = document["source"]
        video = find_video(source["videoFile"], video_root)
        provenance = verify_video(video, source.get("videoSha256"))

        # With --local the caller means each file's OWN clock, so nothing is
        # converted and the panels are NOT one instant. The sheet says so.
        local = (reference_seconds if local_clock
                 else reference_to_local(document, reference_seconds))
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
                       frame, shown_at, quality, guessed, counts,
                       provenance["verified"]))
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
            "videoVerified": provenance["verified"],
            "videoSha256": provenance["actual"],
            "keypointFileSha256": (document.get("_readFrom") or {}).get("sha256"),
            "topologyGuessed": guessed,
            **counts,
        })

    gap, strip, pad, header = 10, 54, 14, 96
    total = sum(panel[1].width for panel in panels) + gap * (len(panels) - 1)
    unsynchronised = local_clock and len(panels) > 1
    if local_clock:
        title = (f"keypoints over the video, at {reference_seconds:.3f} s in "
                 "EACH VIEW'S OWN clock")
    else:
        title = (f"keypoints over the video, at {reference_seconds:.3f} s "
                 "on the reference clock")
    tools = sorted({
        (document.get("model") or {}).get("tool", "unnamed")
        for document in documents
    })
    legend = ("solid joint seen, faint joint barely seen, absent not seen.")
    if unsynchronised:
        # Two panels side by side READ as one moment. If nobody has measured
        # how these cameras line up, saying so quietly in a caption is not
        # enough, because the layout itself makes the claim.
        legend = ("THESE TWO VIEWS ARE NOT ONE MOMENT: no offset between "
                  "these cameras has been measured.")
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
    canvas.text((pad, 54), legend, font=label,
                fill=(255, 140, 120) if unsynchronised else (170, 170, 180))

    # Provenance, VERIFIED rather than asserted. A mismatch never reaches here
    # because it refuses, so this line says either "checked and it holds" or
    # "the file made no claim to check", and never nothing at all.
    checked = [panel[7] for panel in panels]
    if all(state is True for state in checked):
        note, colour = ("video verified by hash against the recording the "
                        "keypoints name"), (150, 190, 150)
    elif any(state is True for state in checked):
        note, colour = ("SOME VIEWS UNVERIFIED: a keypoint file carries no "
                        "video hash to check"), (255, 200, 120)
    else:
        note, colour = ("VIDEO NOT VERIFIED: the keypoint files carry no video "
                        "hash to check against"), (255, 200, 120)
    canvas.text((pad, 72), note, font=label, fill=colour)

    x = pad
    for view, picture, frame, shown_at, quality, guessed, counts, verified in panels:
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
    parser.add_argument("--local", action="store_true",
                        help="read --at as each file's OWN clock, for a view "
                             "whose offset has never been measured")
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
                            video_root=arguments.video_root,
                            local_clock=arguments.local)
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
