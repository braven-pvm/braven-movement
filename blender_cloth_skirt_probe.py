"""Settle a flared skirt on a posed landing with Blender's own cloth simulation.

THE QUESTION THIS ANSWERS. The rendered athlete's kit is fitted, because MPFB
garments are PROXIES: a proxy is fitted to the body by construction and rides it,
so it can never clip and can never flare. A netball skirt is a loose garment. The
character lane hand-modelled one and spent eight landing iterations stopping it
from clipping the thighs. This asks whether Blender's own cloth simulation, which
is free and already installed, drapes a loose skirt on a LANDING without a hand.

    blender -b --python-exit-code 9 -P blender_cloth_skirt_probe.py -- \
        --job spikes/poc-output/netball_double_foot_landing.job.json \
        --output <directory> --phase land --phase absorb

WHY A LANDING AND NOT A STANDING POSE. `netball_double_foot_landing` grades the
knee at `land` and `absorb`, so the knee must stay visible. A skirt that hangs
correctly in `ready` and clips on the landing has answered nothing.

WHAT IS PARAMETERISED AND WHY THAT IS THE POINT. A hand-modelled garment carries
no numbers, so a second one costs what the first did. Every shape below is a
named value, and a hockey skirt is this file with four of them changed.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

from blender_movement_render import (  # noqa: E402
    Studio,
    pose_phase,
)
from blender_mpfb_reference_catch import (  # noqa: E402
    load_reference_catch_config,
    render_view,
)

# ---------------------------------------------------------------- the garment

# THE SHAPE, IN METRES ON THE RENDERED ATHLETE.
#
# A netball skirt is a truncated cone: a waistband ring, a wider hem ring, and
# the panel between them. These five numbers are the whole shape, and they are
# what a second skirt changes.
SKIRT = {
    # Where the waistband sits, as a drop below the pelvis bone's head.
    # Negative tucks it UP under the bodice hem, which is where a netball
    # skirt's band actually sits and where it stops reading as a separate lump.
    "waistDropM": -0.020,
    # The waistband. Snug, because it is pinned and never simulated.
    "waistRadiusM": 0.170,
    # THE FLARE. This one number is the difference between a skirt and a tube,
    # and it is the number the fitted-proxy route cannot express at all.
    "hemRadiusM": 0.255,
    # Waist to hem. Mid-thigh: long enough to be a skirt, short enough that the
    # knee this drill grades stays visible.
    "lengthM": 0.310,
    # WHERE THE WIDENING HAPPENS, and the first version had no such control.
    # 1.0 is a straight cone, which widens from the very top and gave a short
    # wide TUBE that Marius called a blanket. Above 1.0 the panel stays near the
    # hip through the upper skirt and opens near the hem, which is what an
    # A-line is.
    "flarePower": 2.4,
    # Resolution. Radial segments decide how round the hem reads; rings decide
    # how many folds the fabric can carry. Twelve rings cannot fold at all.
    "segments": 72,
    "rings": 24,
}

# THE CLOTH, all Blender's own settings.
#
# Nothing here is exotic. The defaults drape a tablecloth; a light synthetic
# sports fabric is lighter, stiffer against stretch and much softer in bending.
CLOTH = {
    "quality": 10,
    # Heavier than the first attempt. A light cloth with stiff bending holds its
    # own shape and stands off the leg; a heavier, softer one falls.
    "massKg": 0.45,
    "tensionStiffness": 8.0,
    # HIGH, AND IT IS NOT THE SAME KNOB AS BENDING. A soft cloth pinned on a
    # ring narrower than the hip beneath it is pushed outward, and with low
    # compression it BUCKLES into a roll at the waist. That roll is what made
    # the second attempt read as a towel tucked in at the top.
    "compressionStiffness": 15.0,
    "shearStiffness": 2.0,
    # THE NUMBER THAT DECIDES DRAPE. At 0.20 the skirt was a rigid shell that
    # happened not to intersect the leg. Sports fabric bends almost freely.
    # BENDING SETS THE SIZE OF A FOLD, and it is not a drape/rigid switch.
    # At 0.20 with twelve rings the skirt was a rigid shell. At 0.02 with
    # thirty-two it corrugated into fine horizontal ripples, like a lampshade:
    # near-zero bending folds at the smallest scale the mesh allows. The fold
    # scale is set by this number AGAINST the ring spacing, so raising the
    # resolution without raising this trades a stiff skirt for a ribbed one.
    "bendingStiffness": 0.30,
    "airDamping": 1.0,
    # How far the cloth stays off the body. Too small and it passes through;
    # too large and the skirt floats.
    # Thinner. At 0.010 the fabric floats a centimetre off the body on every
    # side, which reads as felt rather than as a jersey knit.
    "collisionDistanceM": 0.004,
    "collisionQuality": 5,
    "selfCollision": True,
    "selfDistanceM": 0.006,
    # How many frames the skirt is given to fall from its build shape onto the
    # pose. THIS IS THE PER-POSE COST and it is the number that decides whether
    # the method scales to an animation.
    # More frames, because a softer cloth takes longer to stop moving. A skirt
    # still swinging when the shutter opens is a skirt in the wrong place.
    "settleFrames": 45,
}


def build_skirt(name: str, origin: Vector, params: dict) -> bpy.types.Object:
    """A truncated cone from the waist ring to the hem ring, and its pin group.

    Built in world space around `origin`, which is the posed pelvis, so the
    skirt starts OUTSIDE the body it is about to fall onto. Built around the
    rest body it would begin interpenetrated, and a cloth solver asked to
    resolve an initial interpenetration explodes rather than settles.
    """
    segments, rings = params["segments"], params["rings"]
    waist_r, hem_r = params["waistRadiusM"], params["hemRadiusM"]
    length = params["lengthM"]
    top = origin.z - params["waistDropM"]

    vertices, faces = [], []
    for ring in range(rings + 1):
        fraction = ring / rings
        # A-LINE, NOT A CONE. The radius opens late, so the panel follows the
        # hip through the upper skirt and flares towards the hem.
        radius = waist_r + (hem_r - waist_r) * (fraction ** params["flarePower"])
        height = top - length * fraction
        for step in range(segments):
            angle = 2.0 * math.pi * step / segments
            vertices.append((
                origin.x + radius * math.cos(angle),
                origin.y + radius * math.sin(angle),
                height,
            ))
    for ring in range(rings):
        for step in range(segments):
            a = ring * segments + step
            b = ring * segments + (step + 1) % segments
            faces.append((a, b, b + segments, a + segments))

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    # SMOOTH, OR IT READS AS PAPER. Flat-shaded quads give every fold a hard
    # facet and the first render of this skirt looked like a folded napkin. The
    # simulation was already correct; only the shading normals were not.
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    # THE PIN GROUP IS THE WAISTBAND. Without it the whole skirt falls to the
    # floor: a cloth object with no pinned vertices is a dropped sheet.
    group = obj.vertex_groups.new(name="pin")
    # TWO RINGS, NOT ONE. A single pinned ring is a pinned LINE: the fabric
    # immediately below it is free to fold back on itself, which is the other
    # half of the waist roll. Two rings give the band a height and it reads as
    # a band.
    group.add(list(range(segments * 2)), 1.0, "REPLACE")
    return obj


def dress(skirt: bpy.types.Object, colliders: list, cloth: dict) -> None:
    """Give the skirt a cloth modifier and every collider a collision one."""
    modifier = skirt.modifiers.new("Cloth", "CLOTH")
    settings = modifier.settings
    settings.quality = cloth["quality"]
    settings.mass = cloth["massKg"]
    settings.tension_stiffness = cloth["tensionStiffness"]
    settings.compression_stiffness = cloth["compressionStiffness"]
    settings.shear_stiffness = cloth["shearStiffness"]
    settings.bending_stiffness = cloth["bendingStiffness"]
    settings.air_damping = cloth["airDamping"]
    settings.vertex_group_mass = "pin"

    collision = modifier.collision_settings
    collision.distance_min = cloth["collisionDistanceM"]
    collision.collision_quality = cloth["collisionQuality"]
    collision.use_self_collision = cloth["selfCollision"]
    collision.self_distance_min = cloth["selfDistanceM"]

    for body in colliders:
        if any(m.type == "COLLISION" for m in body.modifiers):
            continue
        body.modifiers.new("Collision", "COLLISION")


def settle(skirt: bpy.types.Object, frames: int) -> float:
    """Step the scene so the solver runs, and return the seconds it took.

    The body is posed and static, so the skirt falls from its build shape onto
    the pose. No frame is rendered until this returns.
    """
    scene = bpy.context.scene
    modifier = next(m for m in skirt.modifiers if m.type == "CLOTH")
    modifier.point_cache.frame_start = 1
    modifier.point_cache.frame_end = frames
    started = time.perf_counter()
    for frame in range(1, frames + 1):
        scene.frame_set(frame)
    bpy.context.view_layer.update()
    return time.perf_counter() - started


def parse() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--phase", action="append", default=[])
    parser.add_argument("--no-skirt", action="store_true",
                        help="render the same poses with no garment added")
    return parser.parse_args(argv)


def main() -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):  # pragma: no cover
        pass
    args = parse()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    job = json.loads(args.job.read_text(encoding="utf-8"))

    studio = Studio(load_reference_catch_config(args.config))
    studio.add_ball(job["phases"][0]["ball"]["radiusM"])
    rig, human, assets = studio.rig, studio.human, studio.assets

    wanted = args.phase or [p["name"] for p in job["phases"]]
    phases = [p for p in job["phases"] if p["name"] in wanted]
    if not phases:
        raise SystemExit(f"no phase matches {wanted}")

    timings = []
    for phase in phases:
        centre, _ = pose_phase(
            rig, phase, job["anatomyLimitsDegrees"], studio.basis,
            studio.foot_baseline, studio.config.finger_curl_degrees,
            job.get("knuckleLimitsDegrees"), human,
        )
        studio.ball.location = centre
        bpy.context.view_layer.update()

        seconds = 0.0
        skirt = None
        if not args.no_skirt:
            pelvis = rig.matrix_world @ rig.pose.bones["pelvis"].head
            skirt = build_skirt(f"skirt_{phase['name']}", pelvis, SKIRT)
            dress(skirt, [human] + list(assets), CLOTH)
            seconds = settle(skirt, CLOTH["settleFrames"])
            timings.append({"phase": phase["name"], "settleSeconds": round(seconds, 2)})
            print(f"[skirt] {phase['name']} settled {CLOTH['settleFrames']} "
                  f"frames in {seconds:.2f}s", flush=True)

        for name, view in job["views"].items():
            path = output / f"{job['movementId']}.{phase['name']}.{name}.png"
            render_view(
                studio.camera,
                path=path,
                resolution=tuple(view["resolutionPx"]),
                location=Vector(view["locationM"]),
                target=Vector(view["targetM"]),
                lens=view["lensMm"],
                sensor_width=view["sensorWidthMm"],
                world_colour=studio.world_colour,
            )
            print(f"[skirt] wrote {path.name}", flush=True)

        if skirt is not None:
            # One skirt per pose. A settled skirt carries the pose it settled
            # on, so reusing it for the next phase would draw the landing's
            # folds on the absorb.
            bpy.data.objects.remove(skirt, do_unlink=True)

    receipt = output / "cloth-skirt.json"
    receipt.write_text(json.dumps({
        "movementId": job["movementId"],
        "skirt": SKIRT,
        "cloth": CLOTH,
        "timings": timings,
    }, indent=2), encoding="utf-8")
    print(f"[skirt] receipt {receipt}", flush=True)


if __name__ == "__main__":
    main()
