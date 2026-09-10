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
    make_fabric_material,
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
    # ON THE HIP, NOT THE WAIST, and the sign of this reversed twice.
    #
    # Tucked UP under the bodice at -0.020 the panel is pinned ABOVE THE WIDEST
    # PART OF THE FIGURE, and fabric hung from there has to pass over a wider
    # hip. It cannot, so it catches and GATHERS into a ruche at the top. No
    # stiffness setting fixes that: it is a circumference problem, not a
    # material one. A netball skirt sits ON the hips, where nothing below the
    # pin is wider than the pin.
    "waistDropM": -0.020,
    # The waistband. Snug, because it is pinned and never simulated.
    # Only a FALLBACK now. The band is measured off the body ray by ray; this
    # is what a ray that hits nothing uses, and a run that reports many misses
    # is a run whose band is a circle again.
    "waistRadiusM": 0.170,
    # How far outside the skin the band sits. A waistband is not painted on.
    # FLAT AGAINST THE BODICE. At 0.012 the band stood off far enough to read
    # as a band of its own, and a netball dress has none: the skirt is attached
    # under the bodice hem. This is now a seam allowance, not a waistband.
    "waistStandoffM": 0.012,
    # THE FLARE. This one number is the difference between a skirt and a tube,
    # and it is the number the fitted-proxy route cannot express at all.
    # AT REST, ONLY SLIGHTLY WIDER THAN THE HIP.
    #
    # THE REFERENCE SKIRT DOES NOT FLARE STANDING STILL. Eight photographs show
    # it hanging close to the thigh, opening at the hem by very little; the wide
    # flare appears only on a JUMP, and it is a property of LIGHT FABRIC IN
    # MOTION rather than of the garment's cut. Every earlier value here was the
    # IN-FLIGHT shape built as a rest shape, which is a heavy static cone: the
    # towel. 0.195 against a 0.170 hip is a near-tube, and the air does the rest.
    "hemRadiusM": 0.255,
    # Waist to hem. Mid-thigh: long enough to be a skirt, short enough that the
    # knee this drill grades stays visible.
    # SHORT. The reference hem sits at UPPER thigh, roughly a third of the way
    # from crotch to knee, which is about 20 to 25 cm of panel below the hip.
    "lengthM": 0.310,
    # WHERE THE WIDENING HAPPENS, and the first version had no such control.
    # 1.0 is a straight cone, which widens from the very top and gave a short
    # wide TUBE that Marius called a blanket. Above 1.0 the panel stays near the
    # hip through the upper skirt and opens near the hem, which is what an
    # A-line is.
    # Matters much less once the static flare is small. Kept gentle so the
    # panel follows the hip and opens a little towards the hem.
    "flarePower": 2.4,
    # HOW FAR DOWN THE PANEL IS FITTED TO THE FIGURE rather than to the cone.
    # 0 is the old behaviour, a band fit and nothing else. The upper skirt has
    # to clear the hip, which is wider than the waist; below this the skirt is
    # free and the flare decides it.
    "fitToBodyFraction": 0.05,
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
    # BACK UP, AND THIS IS THE FINDING OF THE THIN PASS.
    #
    # "Thin" is not soft. Lowering mass to 0.18 with bending to 0.15 to make the
    # skirt read as light fabric CRUMPLED it: soft cloth folds at a small scale
    # and a mass of small folds reads as MORE fabric, like crushed velvet, not
    # less. A thin garment reads thin from its HEM EDGE, its MATERIAL and how
    # close it sits, never from how easily it creases.
    # LIGHT, because the hem has to LIFT on a jump. The 0.45 that drapes a wide
    # static cone is a fabric that cannot fly, and the reference flare is
    # entirely a flying hem. The crumpling this caused before was on a WIDE
    # skirt with excess fabric to fold; a near-fitted panel has far less.
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


def fit_ring(surfaces: list, origin: Vector, height: float, segments: int,
             fallback: float, standoff: float) -> tuple[list, int]:
    """The worn figure's own radius at the waistband height, angle by angle.

    A HIP IS NOT A CIRCLE. It is roughly an ellipse, wider across than front to
    back, and a circular waistband on it touches at the sides and stands off at
    the front and back. That gap is what made the third attempt read as a hoop
    the skirt hangs from rather than as a band on a body.

    SO THE BAND IS MEASURED, AND IT IS MEASURED AGAINST WHAT IS ACTUALLY THERE.
    A first version cast against the body alone and got 0 hits out of 72. MPFB
    DELETES THE BODY UNDER THE CLOTHES: the human carries a mask modifier named
    `Delete.female_casualsuit02`, so at the hip there is no skin to hit, from
    inside or out. The surface at a waistband is the garment, which is also
    where a real skirt sits. Every candidate is cast and the NEAREST hit wins.

    A miss keeps the fallback radius, and the caller is told how many missed,
    because a band fitted from nothing is a circle again and looks fitted.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = [surface.evaluated_get(depsgraph) for surface in surfaces]
    start = Vector((origin.x, origin.y, height))
    radii, hits = [], 0
    for step in range(segments):
        angle = 2.0 * math.pi * step / segments
        direction = Vector((math.cos(angle), math.sin(angle), 0.0))
        nearest = None
        for surface in evaluated:
            to_local = surface.matrix_world.inverted()
            found, location, _, _ = surface.ray_cast(
                to_local @ start, to_local.to_3x3() @ direction, distance=0.6,
            )
            if not found:
                continue
            reach = (surface.matrix_world @ location - start).length
            nearest = reach if nearest is None else min(nearest, reach)
        if nearest is None:
            radii.append(fallback)
        else:
            hits += 1
            radii.append(nearest + standoff)
    return radii, hits


def build_skirt(name: str, origin: Vector, params: dict,
                body: list | None = None,
                material=None) -> bpy.types.Object:
    """A skirt from a fitted waistband to a circular hem, and its pin group.

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
    fitted_rings, total_rays = 0, 0
    for ring in range(rings + 1):
        fraction = ring / rings
        height = top - length * fraction
        # THE CONE THIS RING WOULD BE ON ITS OWN.
        cone = waist_r + (hem_r - waist_r) * (fraction ** params["flarePower"])

        # AND THE FIGURE'S OWN RADIUS AT THIS HEIGHT, over the upper skirt.
        #
        # Fitting the waistband alone was not enough and the failure is
        # geometric: THE HIP IS WIDER THAN THE WAIST. A near-straight tube hung
        # from a fitted band cannot pass over it, so the fabric catches and
        # GATHERS into a ruche at the top — which is a worse towel cue than the
        # rolled band it replaced. A skirt is fitted THROUGH the hip and flares
        # below it, so the body is measured at every ring of the upper skirt.
        measured = None
        if body is not None and fraction <= params["fitToBodyFraction"]:
            radii, hits = fit_ring(body, origin, height, segments, cone,
                                   params["waistStandoffM"])
            total_rays += segments
            if hits:
                fitted_rings += 1
                measured = radii

        for step in range(segments):
            angle = 2.0 * math.pi * step / segments
            # NEVER INSIDE THE BODY. The larger of the two, so the panel clears
            # the figure where the figure is wide and follows the cone where it
            # is not.
            radius = cone if measured is None else max(measured[step], cone)
            vertices.append((
                origin.x + radius * math.cos(angle),
                origin.y + radius * math.sin(angle),
                height,
            ))

    if body is not None:
        print(f"[skirt] profile fitted on {fitted_rings} ring(s), "
              f"{total_rays} rays cast", flush=True)
        if fitted_rings == 0:
            print("[skirt] WARNING: no ring found the body, so the panel is a "
                  "plain cone and only looks fitted", flush=True)
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
    if material is not None:
        # THE SAME KIT MATERIAL THE BODICE WEARS, so the two routes are compared
        # on SHAPE and not on shading. White matte default is a towel cue of its
        # own, and it is not the thing under test.
        obj.data.materials.append(material)

    # THE PIN GROUP IS THE WAISTBAND. Without it the whole skirt falls to the
    # floor: a cloth object with no pinned vertices is a dropped sheet.
    group = obj.vertex_groups.new(name="pin")
    # TWO RINGS, AND I REVERSED THIS ONCE AND WAS WRONG.
    #
    # A single pinned ring is a pinned LINE, and the fabric immediately below it
    # folds back on itself into a ruche. I had that finding, bought with a
    # render, and dropped to one ring on the theory that the second was what
    # gave the band its HEIGHT and therefore its towel look. It was not. The
    # HEIGHT came from waistStandoffM holding the panel proud of the body; the
    # second ring only stops the fold-back. Two separate causes wearing one
    # symptom, and I changed the wrong one.
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

    fabric = make_fabric_material(studio.config.presentation)

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
            skirt = build_skirt(f"skirt_{phase['name']}", pelvis, SKIRT,
                                [human] + list(assets), fabric)
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
