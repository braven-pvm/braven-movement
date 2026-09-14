"""Author a cosmetic wrist flick on one drill, and measure what it costs.

    blender -b --python-exit-code 9 -P scripts/author_wrist_flick.py -- \\
        --flick config/flick/netball_chest_pass.flick.v1.json --out out/flick

RULED COSMETIC, SHAPE C, by Marius on 2026-09-11: the ball's speed stays
authored by the play and the flick sits on top of the solve. So NOTHING here
changes an engine file and nothing writes to `spikes/movements/`, which is
gate 4. Two levers, both of them arguments the engine already takes:

THE WRIST is pitched by rotating the frame's own `fingerDirection` and
`palmNormal` about their cross product, which is the flexion axis in the
hand's own frame. The frame dictionary is deep-copied and the engine's own
`pose_phase` is then called on the copy, so the solve, the anatomy limits and
the girdle guard all still apply. No axis is guessed and no world axis is
used.

THE FINGERS ARE LEFT ALONE, and that is a measured decision rather than a
gap. The one-frame 53-degree straightening is not a choice of angle: the
engine sets every knuckle to zero flexion and then returns early when no ball
radius is passed, so the snap IS that early return. Letting the grip solve run
on against the receding ball was tried and does the OPPOSITE -- the fingers
claw to 73 degrees, because a knuckle that cannot reach is left at the
furthest the joint permits. Spreading the snap needs one new optional knuckle
argument in an engine file, which is a separate unit. Refer to
`keeps_reaching` for the numbers.

WHAT IT MEASURES, because a flick that looks right and costs a coach a
visible intersection is not a flick that ships:

  wrist, finger   elbow-wrist-knuckle and wrist-knuckle-tip, the paper's own
                  conventions, so the numbers can be read beside its tables.
  inside, deepest the receipt's own `bodyClearanceMm`, per frame, shipped
                  against flicked. The held frames carry 0.37 mm of budget at
                  this tip and the flick must not spend it.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for extra in (REPO, REPO / "spikes"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import bpy  # noqa: E402
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import blender_movement_render as R  # noqa: E402
from blender_mpfb_reference_catch import (  # noqa: E402
    pose_articulated_hand,
    world_head,
    world_tail,
)
from reference_pose_config import load_reference_catch_config  # noqa: E402

# `blender_mpfb_reference_catch.py:398` builds every digit bone name as
# f"{digit}_{index:02d}_{side}", so the middle finger's knuckle is
# `middle_01_l` and its distal bone is `middle_03_l`. The paper's finger angle
# is wrist-knuckle-TIP, and the tip is that bone's TAIL rather than any bone's
# head, which is how `finger_surface_clearance` reads it.
KNUCKLE = {side: f"middle_01_{side}" for side in ("l", "r")}
DISTAL = {side: f"middle_03_{side}" for side in ("l", "r")}


def angle_at(middle: Vector, first: Vector, second: Vector) -> float:
    """The angle first-middle-second in degrees. 180 is a straight line."""
    one, two = (first - middle), (second - middle)
    if one.length < 1e-9 or two.length < 1e-9:
        return float("nan")
    cosine = max(-1.0, min(1.0, one.normalized().dot(two.normalized())))
    return math.degrees(math.acos(cosine))


def hand_angles(rig, side: str) -> tuple[float, float]:
    """The wrist and finger angles in the paper's conventions.

    wrist   elbow-wrist-knuckle, so 180 is a straight line and less is flexion.
    finger  wrist-knuckle-tip at the middle finger, so 180 is a straight finger.
    """
    elbow = world_head(rig, f"lowerarm_{side}")
    wrist = world_head(rig, f"hand_{side}")
    knuckle = world_head(rig, KNUCKLE[side])
    tip = world_tail(rig, DISTAL[side])
    return angle_at(wrist, elbow, knuckle), angle_at(knuckle, wrist, tip)


def pitched(frame: dict, degrees: float) -> dict:
    """A copy of the frame with both hands pitched toward flexion.

    The axis is `fingerDirection` crossed with `palmNormal`: the wrist's own
    flexion axis, read off the job rather than chosen. Flexion is the sense
    that brings the fingers toward the palm side, which is the NEGATIVE
    rotation about that axis, and the caller proves the sense by reading the
    elbow-wrist-knuckle angle afterwards rather than trusting this comment.
    """
    changed = json.loads(json.dumps(frame))
    for side in ("l", "r"):
        hand = changed["hands"][side]
        finger = Vector(hand["fingerDirection"])
        palm = Vector(hand["palmNormal"])
        axis = finger.cross(palm)
        if axis.length < 1e-9:
            continue
        turn = Matrix.Rotation(math.radians(-degrees), 4, axis.normalized())
        hand["fingerDirection"] = list(turn @ finger)
        hand["palmNormal"] = list(turn @ palm)
    return changed


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description="author a cosmetic wrist flick")
    parser.add_argument("--flick", type=Path, required=True)
    parser.add_argument("--job", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--no-render", action="store_true")
    args = parser.parse_args(argv)

    flick = json.loads(args.flick.read_text(encoding="utf-8"))
    job_path = args.job or (
        REPO / "spikes" / "poc-output" / f"{flick['movementId']}.job.json"
    )
    job = json.loads(job_path.read_text(encoding="utf-8"))
    frames = job.get("frames") or []
    if not frames:
        raise SystemExit(
            f"{job_path} carries no frames. Export it with --every=1: a flick is "
            f"a thing that happens over frames and the phase checkpoints cannot "
            f"show it."
        )
    release = next(p["frame"] for p in job["phases"] if p["name"] == "release")
    window = int(flick["flickWindowFrames"])
    # The paper's name. Zero in this version, for the reason the flick
    # file records under followThroughProvenance.
    extend = int(flick["followThroughFrames"])
    pitch = float(flick["wristPitchDegrees"])
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)

    config = load_reference_catch_config()
    studio = R.Studio(config)
    # THE BALL HAS TO BE ASKED FOR. `Studio.__init__` sets `self.ball = None`
    # and only `add_ball` creates it, so the first two render passes framed a
    # camera on a ball that was not in the scene and the hands read as miming.
    # A flick cannot be judged without the thing it is flicking.
    studio.add_ball(frames[0]["ball"]["radiusM"])
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    camera = studio.camera

    # The frames worth looking at and worth measuring: the window, the release
    # and the extension. Not the whole 96, because a flick is 14 frames long
    # and rendering the rest proves nothing.
    interesting = list(range(release - window, release + extend + 1))

    def progress(number: int) -> float:
        """0 at the window's start, 1 at the release frame, 1 after it."""
        if number >= release:
            return 1.0
        return max(0.0, (number - (release - window)) / float(window))

    def keeps_reaching(number: int) -> bool:
        """Always False, and the reason is a measurement rather than a choice.

        THE FINGER SNAP CANNOT BE SPREAD FROM OUTSIDE THE ENGINE. The snap is
        not a choice of angle: `pose_articulated_hand` sets every knuckle to
        0.0 degrees of flexion, a straight finger, and then RETURNS EARLY when
        `ball_radius is None` (`blender_mpfb_reference_catch.py:696`). That
        early return is the jump the paper measures.

        The obvious way round it from outside was to let the grip solve keep
        running for a few frames after the release, against the ball's own
        receding centre, so the fingers would straighten as the tips stopped
        being able to reach. MEASURED, IT DOES THE OPPOSITE. The solve flexes
        a knuckle until the tip reaches the surface and, when it cannot reach
        even fully flexed, its own comment says it will "leave it at the
        furthest the joint permits rather than straight". So the fingers CLAW:
        at frames 77 to 82 of the chest pass they went to 73 degrees against a
        held 114.71, which is more flexed than the grip, not less.

        Spreading the snap therefore needs `pose_articulated_hand` to accept a
        knuckle angle, which it does not expose: one new optional parameter in
        an engine file. That is a separate unit and NOT gate 4. This flick
        leaves the fingers alone and moves the wrist, which is authorable from
        outside and costs nothing.
        """
        return False

    rows = []
    crops = []
    HELD_KNUCKLE = 0.0
    RELEASED_KNUCKLE = 0.0

    def pose_and_read(frame: dict, number: int, flicked: bool) -> dict:
        use = pitched(frame, pitch * progress(number)) if flicked else frame
        centre, receipt = R.pose_phase(
            studio.rig, use, job["anatomyLimitsDegrees"], studio.basis,
            studio.foot_baseline, config.finger_curl_degrees,
            job.get("knuckleLimitsDegrees"),
        )
        if flicked and keeps_reaching(number):
            # The ball's own centre at this frame, and the job's own radius.
            # Nothing here is a phantom: the grip solve is simply allowed to
            # keep running for a few frames after the release, against a ball
            # that is leaving.
            for side in ("l", "r"):
                pose_articulated_hand(
                    studio.rig, side=side, ball_centre=centre,
                    finger_curl_degrees=config.finger_curl_degrees,
                    # `blender_movement_render.py:533` reads the radius off the
                    # frame's own ball block, not off the job or the config.
                    ball_radius=frame["ball"]["radiusM"],
                    knuckle_limits=job.get("knuckleLimitsDegrees"),
                )
        wrist, finger = hand_angles(studio.rig, "l")
        body = receipt.get("bodyClearanceMm") or {}
        # HAND AGAINST HAND, because the flick pitches BOTH wrists inward and
        # the renders showed the fingertips closing on each other at frames 74
        # and 75. `bodyClearanceMm` measures the body against the ball and
        # would not see two hands meeting, so this is measured here.
        tips = {
            side: world_tail(studio.rig, DISTAL[side]) for side in ("l", "r")
        }
        return {
            "frame": number,
            "flicked": flicked,
            "holding": bool(frame["ball"].get("holding")),
            "wrist": round(wrist, 2),
            "finger": round(finger, 2),
            "inside": body.get("verticesInside", 0),
            "deepestMm": round(body.get("deepestMm", 0.0), 2),
            "tipGapMm": round((tips["l"] - tips["r"]).length * 1000.0, 1),
            "ballCentre": [round(v, 4) for v in centre],
        }

    # THE RELEASED KNUCKLE IS READ, NOT ASSUMED. Pose the frame after release
    # as the engine does and measure where the fingers land, so the ramp runs
    # between two measured angles instead of the paper's printed ones.
    after = next(f for f in frames if f["frame"] == release + 1)
    RELEASED_KNUCKLE = pose_and_read(after, release + 1, False)["finger"]
    held = next(f for f in frames if f["frame"] == release - 1)
    HELD_KNUCKLE = pose_and_read(held, release - 1, False)["finger"]
    print(f"[flick] measured: held finger {HELD_KNUCKLE:.2f}, "
          f"released finger {RELEASED_KNUCKLE:.2f}, "
          f"snap {RELEASED_KNUCKLE - HELD_KNUCKLE:.2f} degrees in one frame")

    view = job["views"]["quarter"]
    for number in interesting:
        frame = next((f for f in frames if f["frame"] == number), None)
        if frame is None:
            continue
        for flicked in (False, True):
            row = pose_and_read(frame, number, flicked)
            rows.append(row)
            if args.no_render:
                continue
            # FRAME THE BALL AND BOTH HANDS, not the wrist alone. The first
            # pass aimed at `hand_l` at 135 mm and left the ball out of shot
            # entirely, so the hands read as miming and the one thing a flick
            # has to be judged against was missing. The target is the midpoint
            # of the ball and the two wrists, and the lens is wide enough to
            # hold all three.
            ball_here = Vector(row["ballCentre"])
            # The ball alone. `blender_movement_render.py:668` says the seams
            # are parented to it, "so moving the ball still moves the whole
            # thing"; moving them too would move them twice.
            studio.ball.location = ball_here
            # THE JOB'S OWN CAMERA, THEN A CROP. Five hand-placed cameras went
            # wrong in five different ways: aiming at the wrist left the ball
            # out of shot, centring the ball eclipsed the hand, 0.46 m on an
            # 80 mm lens framed a forearm, and looking along the flexion axis
            # put the camera inside her shoulder because the sign rule chose
            # the direction into the body.
            #
            # So the camera is no longer placed here at all. It is the view the
            # job ships, which is a proven whole-figure framing that cannot end
            # up inside the athlete, and the hand is found afterwards by
            # PROJECTING it into the image with `world_to_camera_view` and
            # cropping around where it actually landed. A crop is arithmetic in
            # two dimensions and has no way to be inside anything.
            camera.data.lens = view["lensMm"]
            camera.data.sensor_width = view["sensorWidthMm"]
            camera.location = Vector(view["locationM"])
            camera.rotation_euler = (
                Vector(view["targetM"]) - camera.location
            ).to_track_quat("-Z", "Y").to_euler()
            wide, high = view["resolutionPx"]
            scene.render.resolution_x, scene.render.resolution_y = wide, high
            whole = out / f"whole_f{number:03d}_{'flick' if flicked else 'ship'}.png"
            scene.render.filepath = str(whole)
            bpy.ops.render.render(write_still=True)

            # Where the measured hand and the ball landed, in image pixels.
            measured = world_head(studio.rig, "hand_l")
            spots = []
            for point in (measured, ball_here):
                uv = world_to_camera_view(scene, camera, point)
                spots.append((uv.x * wide, (1.0 - uv.y) * high))
            crops.append({
                "frame": number,
                "flicked": flicked,
                "whole": whole.name,
                "handPx": [round(v, 1) for v in spots[0]],
                "ballPx": [round(v, 1) for v in spots[1]],
            })

    header = ("frame", "hold", "wristShip", "wristFlick", "fingShip",
              "fingFlick", "insideS", "insideF", "deepestS", "deepestF",
              "tipGapS", "tipGapF")
    print("\n[flick] " + "".join(f"{name:>11}" for name in header))
    for number in interesting:
        ship = next((r for r in rows if r["frame"] == number and not r["flicked"]), None)
        kick = next((r for r in rows if r["frame"] == number and r["flicked"]), None)
        if ship is None or kick is None:
            continue
        cells = (
            f"{number}", f"{ship['holding']}",
            f"{ship['wrist']:.2f}", f"{kick['wrist']:.2f}",
            f"{ship['finger']:.2f}", f"{kick['finger']:.2f}",
            f"{ship['inside']}", f"{kick['inside']}",
            f"{ship['deepestMm']:.2f}", f"{kick['deepestMm']:.2f}",
            f"{ship['tipGapMm']:.1f}", f"{kick['tipGapMm']:.1f}",
        )
        print("[flick] " + "".join(f"{cell:>11}" for cell in cells))

    (out / "flick_measurements.json").write_text(
        json.dumps({
            "movementId": flick["movementId"],
            "flickFile": args.flick.resolve().relative_to(REPO).as_posix(),
            "releaseFrame": release,
            "windowFrames": window,
            "extendFrames": extend,
            "wristPitchDegrees": pitch,
            "heldFingerDegrees": HELD_KNUCKLE,
            "releasedFingerDegrees": RELEASED_KNUCKLE,
            "rows": rows,
            "crops": crops,
        }, indent=2),
        encoding="utf-8",
    )
    print(f"\n[flick] wrote {out / 'flick_measurements.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
