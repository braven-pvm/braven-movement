"""How high off the floor is she IN THE PICTURE? Read from a render, not a solve.

The library has a drill whose phases are `approach, flight, land, absorb`, and
the solve puts her 15.80 cm off the ground at the frame named `flight`. Nothing
in the repository can tell you whether the RENDER does, because nothing reads a
foot height out of an image. This does.

WHY IT RENDERS ITS OWN SILHOUETTE RATHER THAN MEASURING THE COACH RENDER. Look
at `netball_double_foot_landing.flight.side.png`: a white shoe on a light floor
with a dark contact shadow directly under it. The lowest pixel of the ATHLETE
and the lowest pixel of her SHADOW are a few pixels apart and the shadow does
not leave the ground when she does. Any threshold that separates them is a
number I would have chosen, and an instrument whose answer depends on a
threshold I picked cannot referee a change I made. So this hides the floor,
turns the film transparent, and reads the alpha channel. The lowest opaque
pixel IS her lowest point, exactly, with nothing to tune.

IT NEVER READS THE SOLVE. It poses through `pose_phase`, the same call the coach
render uses, and then measures the picture. That is the whole point: it is
downstream of `pose_stance`, so it can disagree with the solve, and it will.

AND IT CARRIES ITS OWN PROOF OF POWER. `--lift-cm` translates the posed rig by a
known amount before rendering. An instrument that reports "flat" on the day it
is written has not been tested -- "flat" is what a broken one reports too. Pass
a lift, and the probe must read that lift back. Only then does a flat reading
mean the render is flat.

    blender -b --python-exit-code 9 -P scripts/flight_probe.py -- \
        --job spikes/poc-output/netball_double_foot_landing.job.json \
        --output out/flight-probe --view side
    blender ... -- --lift-cm 10 --lift-cm 20      # the power test
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bpy
import numpy
from mathutils import Vector

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import blender_movement_render as render  # noqa: E402
# NOT re-exported by the movement renderer, so it is imported from where it is
# defined rather than reached through that module.
from blender_mpfb_reference_catch import point_at  # noqa: E402

# A pixel counts as the athlete above this alpha. It is not a tuned threshold:
# with the film transparent and the floor hidden there is nothing in the scene
# but her, so alpha is 0 or 1 everywhere except the one-pixel antialiased rim.
# Half a pixel of coverage is the rim's midpoint.
OPAQUE = 0.5

# Renders for this probe carry no lighting decision, so they need no sampling.
# The coach render uses 64. Alpha coverage is geometry.
PROBE_SAMPLES = 4


def hide_the_floor() -> str:
    """The floor must not be in the silhouette, or she never leaves it.

    Returned rather than assumed, so the receipt records that it happened. A
    probe that silently failed to hide the floor would report a constant
    lowest row and read exactly like a flattened render.
    """
    floor = bpy.data.objects.get("BRAVEN_Floor")
    if floor is None:
        raise SystemExit(
            "REFUSED. No object named BRAVEN_Floor. `add_floor` names it, so "
            "either the studio changed or this is not the movement renderer, "
            "and a silhouette that still contains a floor measures nothing.")
    floor.hide_render = True
    return floor.name


def lowest_opaque_row(path: Path) -> dict:
    """The bottom of the athlete, in pixels, from the alpha channel.

    Blender images are bottom-up, so row 0 is the BOTTOM of the picture and a
    larger row index is higher in the frame. The value returned is therefore
    "how far up from the bottom edge her lowest pixel is", and it RISES when
    she leaves the ground.
    """
    image = bpy.data.images.load(str(path), check_existing=False)
    width, height = (int(value) for value in image.size)
    buffer = numpy.empty(width * height * 4, dtype=numpy.float32)
    image.pixels.foreach_get(buffer)
    bpy.data.images.remove(image)

    alpha = buffer.reshape(height, width, 4)[:, :, 3]
    rows = numpy.nonzero((alpha > OPAQUE).any(axis=1))[0]
    if not len(rows):
        raise SystemExit(
            f"REFUSED. {path.name} has no opaque pixel at all. The athlete is "
            f"not in this frame, so there is no lowest point to report.")
    lowest = int(rows.min())
    return {
        "lowestRow": lowest,
        "highestRow": int(rows.max()),
        "opaquePixels": int((alpha > OPAQUE).sum()),
        "widthPx": width,
        "heightPx": height,
    }


def centimetres_per_pixel(view: dict) -> dict:
    """The picture's scale where she is standing, and what it assumes.

    Blender's `sensor_fit` is left at AUTO and the renderer never sets it, so
    `sensorWidthMm` applies to the LARGER pixel dimension. These views are
    1080 by 1350, so the sensor is the vertical axis. This was proved on
    2026-09-10 against the ball's own silhouette: predicted outer edge against
    measured, 0.6 to 1.7 px with this fit and 22 to 45 px with the other.

    THE DEPTH IS AN ASSUMPTION AND IT IS THE ONLY ONE HERE. Her feet are taken
    to be at the camera's aim distance. They are not exactly: she stands within
    a few centimetres of the target, and the error is proportional. The
    returned `depthSensitivity` says what 10 cm of depth error costs, so a
    reader can decide whether it matters rather than trust that it does not.

    The PIXEL readings above need none of this and are exact.
    """
    location = numpy.array(view["locationM"], dtype=float)
    target = numpy.array(view["targetM"], dtype=float)
    depth = float(numpy.linalg.norm(target - location))
    longest = max(view["resolutionPx"])
    metres = depth * view["sensorWidthMm"] / (view["lensMm"] * longest)
    return {
        "depthM": round(depth, 4),
        "cmPerPixel": round(metres * 100.0, 6),
        "depthSensitivity": (
            f"a 10 cm error in her depth moves every centimetre figure by "
            f"{10.0 / (depth * 100.0):.1%}"),
    }


def calibrate(readings: list[dict]) -> dict | None:
    """Centimetres per pixel, MEASURED from the lifts instead of assumed.

    `centimetres_per_pixel` has to guess her depth. The lifts do not: a known
    number of centimetres goes in and a number of pixels comes out, through
    the same camera, the same rig and the same render. That is a calibration
    rather than a conversion factor, and it retires the only assumption in
    this file.

    It also checks itself. Every pose is lifted by the same amount, so every
    pose must report the same pixels per centimetre. A spread between them
    would mean the lift is not doing what its name says, and the number must
    not be used.
    """
    lifts = sorted({reading["liftCm"] for reading in readings})
    if len(lifts) < 2:
        return None
    baseline = {r["name"]: r["lowestRow"] for r in readings if not r["liftCm"]}
    slopes = []
    for reading in readings:
        if not reading["liftCm"]:
            continue
        rise = reading["lowestRow"] - baseline[reading["name"]]
        slopes.append(rise / reading["liftCm"])
    low, high = min(slopes), max(slopes)
    # A pixel is the unit here, so two readings of one lift can differ by one
    # pixel from the antialiased rim alone. Over a 10 cm lift that is 0.1.
    agrees = (high - low) <= 0.15
    middle = sum(slopes) / len(slopes)
    return {
        "liftsCm": lifts,
        "pixelsPerCm": round(middle, 4),
        "cmPerPixel": round(1.0 / middle, 6),
        "spreadPixelsPerCm": round(high - low, 4),
        "everyPoseAgrees": agrees,
        "readings": len(slopes),
        "note": (
            "measured from the lifts, not from an assumed depth"
            if agrees else
            "DO NOT USE. The poses disagree about how far one centimetre "
            "moves her, so the lift is not a pure translation."),
    }


def render_silhouette(studio, view: dict, path: Path) -> None:
    scene = bpy.context.scene
    camera = studio.camera
    camera.data.type = "PERSP"
    camera.data.lens = view["lensMm"]
    camera.data.sensor_width = view["sensorWidthMm"]
    camera.location = Vector(view["locationM"])
    point_at(camera, Vector(view["targetM"]))
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = view["resolutionPx"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    # THE TWO LINES THIS WHOLE FILE RESTS ON.
    scene.render.film_transparent = True
    try:
        scene.eevee.taa_render_samples = PROBE_SAMPLES
    except AttributeError:  # pragma: no cover - a different engine build
        pass
    scene.render.filepath = str(path)
    scene.render.use_file_extension = True
    path.unlink(missing_ok=True)
    bpy.ops.render.render(write_still=True)


def lift(studio, centimetres: float) -> None:
    """Move the posed athlete straight up, to prove the probe can see it.

    Every bone that has no parent moves, which is the rig's root, and the ball
    with it. This runs AFTER `pose_phase`, so it does not change the pose --
    it changes only her height, which is exactly the quantity under test.
    """
    if not centimetres:
        return
    shift = Vector((0.0, 0.0, centimetres / 100.0))
    for bone in studio.rig.pose.bones:
        if bone.parent is None:
            bone.matrix.translation = bone.matrix.translation + shift
    if studio.ball is not None:
        studio.ball.location = studio.ball.location + shift
    bpy.context.view_layer.update()


def poses_from(job: dict, which: str) -> list[dict]:
    if which == "phases":
        return list(job["phases"])
    entries = []
    for frame in job["frames"]:
        entry = dict(frame)
        entry["name"] = f"f{frame['frame']:03d}"
        entries.append(entry)
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path,
                        default=render.DEFAULT_CONFIG_PATH)
    parser.add_argument("--view", default="side")
    parser.add_argument("--which", choices=("phases", "frames"),
                        default="phases")
    parser.add_argument("--lift-cm", type=float, action="append", default=None,
                        help="translate the posed rig up by this many "
                             "centimetres before rendering, repeatable. This "
                             "is the probe's power test, not a fix.")
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)

    job = json.loads(args.job.read_text(encoding="utf-8"))
    if args.view not in job["views"]:
        raise SystemExit(
            f"REFUSED. {args.job.name} has no view named {args.view}. It has: "
            f"{', '.join(sorted(job['views']))}.")
    view = job["views"][args.view]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    studio = render.Studio(render.load_reference_catch_config(args.config))
    # NO BALL. `Studio` creates none until `add_ball` is called, and this probe
    # never calls it. The ball is not her foot, and it would be a contaminant
    # in two ways: unplaced it sits at the origin, ON the floor, and would be
    # the lowest opaque pixel in every frame; placed, it is still lower than
    # her shoe whenever she carries it low. `pose_phase` needs no ball object
    # -- it RETURNS the centre and the coach renderer moves the ball itself.
    floor = hide_the_floor()

    lifts = args.lift_cm if args.lift_cm is not None else [0.0]
    if 0.0 not in lifts:
        # THE UNLIFTED READING IS THE MEASUREMENT. A run that only ever lifts
        # her has calibrated the probe and measured nothing.
        lifts = [0.0] + list(lifts)

    readings = []
    for centimetres in lifts:
        for pose in poses_from(job, args.which):
            render.pose_phase(
                studio.rig, pose, job["anatomyLimitsDegrees"], studio.basis,
                studio.foot_baseline, studio.config.finger_curl_degrees,
                job.get("knuckleLimitsDegrees"), studio.human,
            )
            lift(studio, centimetres)
            tag = f"lift{centimetres:g}" if centimetres else "asrendered"
            path = output / (f"{job['movementId']}.{pose['name']}."
                             f"{args.view}.{tag}.png")
            render_silhouette(studio, view, path)
            reading = lowest_opaque_row(path)
            reading.update({
                "name": pose["name"],
                "frame": pose["frame"],
                "liftCm": centimetres,
                "path": str(path),
            })
            readings.append(reading)
            print(f"[flight-probe] {pose['name']:<9} lift {centimetres:5.1f} cm "
                  f"-> lowest opaque row {reading['lowestRow']}")

    scale = centimetres_per_pixel(view)
    measured = calibrate(readings)
    receipt = {
        "movementId": job["movementId"],
        "view": args.view,
        "which": args.which,
        "generatedFrom": studio.build,
        "floorHidden": floor,
        "filmTransparent": True,
        "eeveeSamples": PROBE_SAMPLES,
        "opaqueAbove": OPAQUE,
        "scaleFromCamera": scale,
        "scaleFromLifts": measured,
        "readings": readings,
    }
    path = output / f"{job['movementId']}.{args.view}.flightprobe.json"
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")

    print()
    print(f"[flight-probe] scale from the camera, depth ASSUMED "
          f"{scale['depthM']} m: {scale['cmPerPixel']:.6f} cm per pixel")
    if measured:
        print(f"[flight-probe] scale from the lifts, MEASURED:            "
              f"{measured['cmPerPixel']:.6f} cm per pixel  "
              f"({measured['pixelsPerCm']} px/cm, spread "
              f"{measured['spreadPixelsPerCm']})")
        gap = abs(measured["cmPerPixel"] - scale["cmPerPixel"])
        print(f"[flight-probe] they differ by {gap / scale['cmPerPixel']:.1%}, "
              f"which is the depth assumption and nothing else.")
        if not measured["everyPoseAgrees"]:
            print(f"[flight-probe] {measured['note']}")
    else:
        print("[flight-probe] NO LIFT WAS RUN, so the probe has not been shown "
              "able to report a rise. A flat reading from this run means "
              "nothing. Re-run with --lift-cm.")

    span = max(r["lowestRow"] for r in readings if not r["liftCm"]) - \
        min(r["lowestRow"] for r in readings if not r["liftCm"])
    print(f"[flight-probe] AS RENDERED, her lowest pixel spans {span} px "
          f"across {sum(1 for r in readings if not r['liftCm'])} poses.")
    print(f"[flight-probe] {len(readings)} readings -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
