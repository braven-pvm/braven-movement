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
    keyframe,
    pose_phase,
    render_movie,
    world_head,
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

# HOW MANY FRAMES THE SKIRT GETS BEFORE THE MOVEMENT STARTS.
#
# THIS IS THE WHOLE DIFFERENCE BETWEEN THE TWO ROUTES. Per pose, the skirt is
# built as a lathe and falls onto a body that never moves, so it arrives at a
# deep crouch from directly above, with no speed and nowhere for the fabric to
# go. In a continuous bake the body is held at the first pose for this many
# frames, the cloth falls onto THAT, and then the movement plays under a skirt
# that is already hanging. Every later pose is reached WITH MOMENTUM.
#
# The reference photographs show a hem that flies on the jump and drops on the
# landing. That shape is a property of a moving hem and a per-pose settle
# cannot produce it, because a settle is the definition of no motion.
PREROLL_FRAMES = 30


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


def carry_on_bone(skirt: bpy.types.Object, rig, bone_name: str) -> float:
    """Make the pinned waistband ride the pelvis, and return the fit error.

    A PINNED VERTEX IS PINNED TO THE MODIFIER STACK'S INPUT, NOT TO THE BODY.
    In the per-pose route the body never moves, so a pin holds the waistband
    exactly where `build_skirt` put it. In an animation the pelvis travels most
    of a metre, and a skirt pinned to nothing would hang in the air while she
    jumps out of it.

    So the skirt gets an ARMATURE modifier BEFORE the cloth one, with every
    vertex weighted to the pelvis. The pinned ring then takes its position from
    the armature's output, and the free panel simulates against a waistband
    that moves.

    THE MESH MUST BE UN-POSED FIRST. `build_skirt` writes world coordinates
    around the POSED pelvis. An armature modifier applies the bone's pose
    transform to whatever it is given, so that pose would be applied twice and
    the skirt would leave the figure before the solver runs. Every vertex is
    carried back through the inverse of that transform here.

    THE RETURN VALUE IS THAT CLAIM'S INSTRUMENT, and it exists because a wrong
    transform produces a plausible artefact: a skirt somewhere near a hip, on a
    figure, that no measurement in this file would refuse. It is the largest
    distance in metres between a vertex as `build_skirt` placed it and the same
    vertex after the armature has run. A correct un-pose leaves noise.
    """
    pose_bone = rig.pose.bones[bone_name]
    group = skirt.vertex_groups.new(name=bone_name)
    group.add(list(range(len(skirt.data.vertices))), 1.0, "REPLACE")

    built = [Vector(vertex.co) for vertex in skirt.data.vertices]

    # The armature deform, written out: a vertex goes from the object's space
    # into the armature's, through the bone's pose against its rest, and back.
    # `build_skirt` leaves the object matrix at identity, so object space and
    # world space are the same space here.
    to_world = rig.matrix_world
    channel = (
        to_world
        @ (pose_bone.matrix @ pose_bone.bone.matrix_local.inverted())
        @ to_world.inverted()
    )
    undo = channel.inverted()
    for vertex in skirt.data.vertices:
        vertex.co = undo @ vertex.co

    modifier = skirt.modifiers.new("Carry", "ARMATURE")
    modifier.object = rig
    modifier.use_vertex_groups = True
    modifier.use_bone_envelopes = False

    bpy.context.view_layer.update()
    evaluated = skirt.evaluated_get(bpy.context.evaluated_depsgraph_get())
    landed = evaluated.data.vertices
    return max(
        (landed[index].co - built[index]).length for index in range(len(built))
    )


def read_hem(skirt: bpy.types.Object, rig, params: dict) -> dict:
    """Where the hem is, this frame, against the waist it hangs from.

    THE ONE QUESTION A CONTINUOUS BAKE EXISTS TO ANSWER is whether the hem
    LIFTS on the jump and drops on the landing, because that is where the
    reference photographs get their flare. My eye cannot answer it across six
    panels and has already been wrong about this garment twice, so the run
    measures it.

    THE HEM IS THE LAST RING OF VERTICES. `build_skirt` lathes ring by ring
    from the waist down, and the two modifiers on the stack are both DEFORM
    modifiers, which never add, remove or reorder a vertex. So the final
    `segments` vertices are the hem edge in both meshes.

    Both figures are relative to the pelvis, never to the world. A hem that
    rises because the whole athlete rose has not lifted.
    """
    segments = params["segments"]
    evaluated = skirt.evaluated_get(bpy.context.evaluated_depsgraph_get())
    vertices = evaluated.data.vertices
    hem = [Vector(vertices[i].co) for i in range(len(vertices) - segments,
                                                len(vertices))]
    pelvis = world_head(rig, "pelvis")
    radii = [math.hypot(v.x - pelvis.x, v.y - pelvis.y) for v in hem]
    heights = [v.z - pelvis.z for v in hem]
    floor = min(world_head(rig, f"foot_{side}").z for side in ("l", "r"))
    return {
        "pelvisZ": round(pelvis.z, 4),
        "lowerFootZ": round(floor, 4),
        "hemRadiusM": round(sum(radii) / len(radii), 4),
        "widestHemM": round(max(radii), 4),
        "hemBelowPelvisM": round(sum(heights) / len(heights), 4),
    }


def bake(skirt: bpy.types.Object, first: int, last: int,
         at_frame=None) -> tuple[list[float], float]:
    """Step the whole range once, and return the cost of every frame.

    ONE CLOTH SOLVE OVER THE WHOLE MOVEMENT. The point cache is told the range
    so the solver treats it as one continuous simulation rather than as a
    sequence of restarts.

    Returns the solve seconds frame by frame, and the total seconds spent in
    `at_frame`, which is kept separate so a render never lands in a solve cost.
    """
    scene = bpy.context.scene
    modifier = next(m for m in skirt.modifiers if m.type == "CLOTH")
    modifier.point_cache.frame_start = first
    modifier.point_cache.frame_end = last

    solve, extra = [], 0.0
    for frame in range(first, last + 1):
        started = time.perf_counter()
        scene.frame_set(frame)
        # FORCE THE SOLVE INSIDE THE TIMED REGION. `frame_set` asks the
        # depsgraph for the frame; reading the evaluated mesh is what makes it
        # finish. Without this line the number is the cost of the request.
        evaluated = skirt.evaluated_get(bpy.context.evaluated_depsgraph_get())
        _ = evaluated.data.vertices[0].co
        solve.append(time.perf_counter() - started)
        if at_frame is not None:
            extra += at_frame(frame)
    return solve, extra


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


def animate(studio, job: dict, output: Path, args, fabric) -> dict:
    """One cloth bake over the whole drill, timed, with a sheet and a clip.

    THE QUESTION THIS ANSWERS, and it is not the same one as the per-pose run.
    A settle costs 18 seconds and buys ONE still. If the natural method for a
    movement is one bake over its frames, the cost per frame is what decides
    whether the route scales, and no per-pose number predicts it.
    """
    scene = bpy.context.scene
    rig, human, assets = studio.rig, studio.human, studio.assets
    frames = job.get("frames") or []
    if not frames:
        raise SystemExit(
            "the job carries no frames, so there is nothing to bake over. "
            "Export it with --every=N: cd spikes && pixi run --frozen python "
            f"export_blender_job.py {job['movementId']} --every=2"
        )

    # A previous drill's action would play under this one. Clearing the objects
    # is not enough, because the action itself survives in bpy.data.
    for item in (rig, studio.ball):
        item.animation_data_clear()
    for action in list(bpy.data.actions):
        action.use_fake_user = False
        bpy.data.actions.remove(action)

    preroll = max(1, args.preroll)
    last = preroll + len(frames) - 1
    scene.frame_start, scene.frame_end = 1, last
    fps = max(1, round(job["framesPerSecond"] / max(job["frameStep"], 1)))
    scene.render.fps = fps

    # POSE EVERY FRAME, THEN KEY IT. The frame is set BEFORE the pose is built,
    # because once keys exist a frame change evaluates them and would replace
    # the pose that was just made.
    for index, frame in enumerate(frames):
        number = preroll + index
        scene.frame_set(number)
        centre, _ = pose_phase(
            rig, frame, job["anatomyLimitsDegrees"], studio.basis,
            studio.foot_baseline, studio.config.finger_curl_degrees,
            job.get("knuckleLimitsDegrees"),
        )
        studio.ball.location = centre
        keyframe(rig, studio.ball, number)
        if index == 0:
            # THE PRE-ROLL IS THE FIRST POSE, HELD. The same key at frame 1 and
            # at the start of the movement leaves the body static between them,
            # so the cloth falls onto a pose that is not moving.
            keyframe(rig, studio.ball, 1)
    print(f"[skirt] posed {len(frames)} frames at {fps} fps, "
          f"pre-roll {preroll}, scene 1..{last}", flush=True)

    # THE CONTROL, and it is run before the skirt exists. Stepping this rig
    # costs something on its own, and without that number every second in the
    # bake would be charged to the cloth.
    control = []
    for number in range(1, last + 1):
        started = time.perf_counter()
        scene.frame_set(number)
        _ = human.evaluated_get(
            bpy.context.evaluated_depsgraph_get()).data.vertices[0].co
        control.append(time.perf_counter() - started)
    bare = sum(control) / len(control)
    print(f"[skirt] the rig alone steps at {bare:.3f}s per frame", flush=True)

    scene.frame_set(1)
    bpy.context.view_layer.update()
    pelvis = rig.matrix_world @ rig.pose.bones["pelvis"].head
    skirt = build_skirt("skirt_bake", pelvis, SKIRT, [human] + list(assets),
                        fabric)
    error = carry_on_bone(skirt, rig, "pelvis")
    print(f"[skirt] the waistband rides the pelvis to "
          f"{error * 1000.0:.4f} mm", flush=True)
    if error > 1.0e-4:
        print("[skirt] WARNING: the un-pose is wrong, so the skirt starts in "
              "the wrong place and every frame after it is meaningless",
              flush=True)
    dress(skirt, [human] + list(assets), CLOTH)

    # THE SHEET: the four graded poses, plus the middle of the two longest gaps
    # between them, so the rise and the descent are on the page as well.
    def nearest(source: int) -> int:
        return min(range(len(frames)),
                   key=lambda i: abs(frames[i]["frame"] - source))

    marks = {preroll + nearest(p["frame"]): p["name"] for p in job["phases"]}
    ordered = sorted(marks)
    gaps = sorted(
        ((ordered[i + 1] - ordered[i], i) for i in range(len(ordered) - 1)),
        reverse=True,
    )
    for _, i in gaps[:2]:
        middle = (ordered[i] + ordered[i + 1]) // 2
        marks.setdefault(middle, "between")
    ordered = sorted(marks)
    check = ordered[len(ordered) // 2]

    view = job["views"][args.view]
    recorded: dict[int, list] = {}
    sheet: list[str] = []
    track: list[dict] = []

    def snapshot(number: int) -> float:
        started = time.perf_counter()
        # EVERY FRAME IS MEASURED, and only six are drawn. The seconds this
        # costs are returned with the render's and are not in the solve cost.
        if number >= preroll:
            reading = read_hem(skirt, rig, SKIRT)
            reading["frame"] = number - preroll
            track.append(reading)
        name = marks.get(number)
        if name is None:
            return time.perf_counter() - started
        if number == check:
            evaluated = skirt.evaluated_get(
                bpy.context.evaluated_depsgraph_get())
            recorded[number] = [Vector(v.co) for v in evaluated.data.vertices]
        path = output / (
            f"{job['movementId']}.bake."
            f"{number - preroll:03d}.{name}.{args.view}.png"
        )
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
        sheet.append(path.name)
        print(f"[skirt] wrote {path.name}", flush=True)
        return time.perf_counter() - started

    solve, drawing = bake(skirt, 1, last, snapshot)

    # DOES THE HEM LIFT? Printed as a range, because the answer is a range.
    widest = max(track, key=lambda r: r["hemRadiusM"])
    tightest = min(track, key=lambda r: r["hemRadiusM"])
    feet = {r["lowerFootZ"] for r in track}
    print(
        f"[skirt] hem radius {tightest['hemRadiusM']:.3f}m at frame "
        f"{tightest['frame']} to {widest['hemRadiusM']:.3f}m at frame "
        f"{widest['frame']}, a swing of "
        f"{(widest['hemRadiusM'] - tightest['hemRadiusM']) * 100.0:.1f} cm "
        f"on a built hem of {SKIRT['hemRadiusM']:.3f}m",
        flush=True,
    )
    print(
        f"[skirt] the pelvis moves "
        f"{(max(r['pelvisZ'] for r in track) - min(r['pelvisZ'] for r in track)) * 100.0:.1f}"
        f" cm vertically, and the lower foot takes "
        f"{len(feet)} distinct height(s) over {len(track)} frames",
        flush=True,
    )
    warm = solve[preroll - 1:]
    settling = solve[:preroll - 1]
    print(
        f"[skirt] bake {sum(solve):.1f}s over {last} frames: "
        f"pre-roll {sum(settling):.1f}s, movement {sum(warm):.1f}s for "
        f"{len(warm)} frames = {sum(warm) / len(warm):.3f}s per frame "
        f"(worst {max(warm):.3f}s). Renders took {drawing:.1f}s and are not "
        f"in those numbers.",
        flush=True,
    )

    # DOES THE CACHE SERVE A BACKWARDS JUMP? The movie renders the range again
    # from the start, and if the cache does not answer, the solver restarts
    # from wherever it is and the clip is of a different simulation. So one
    # frame is read during the bake and read again after a jump backwards.
    scene.frame_set(check)
    again = skirt.evaluated_get(bpy.context.evaluated_depsgraph_get())
    drift = max(
        (Vector(v.co) - was).length
        for v, was in zip(again.data.vertices, recorded[check])
    )
    print(f"[skirt] the cache serves frame {check} to "
          f"{drift * 1000.0:.4f} mm after a jump backwards", flush=True)

    movie = None
    if not args.no_movie:
        if drift > 1.0e-4:
            print("[skirt] REFUSING the clip: the cache does not answer a "
                  "backwards jump, so the movie would be of a different "
                  "simulation from the sheet", flush=True)
        else:
            scene.frame_start = preroll
            scene.frame_end = last
            written = render_movie(
                studio.camera,
                path=output / f"{job['movementId']}.bake.mp4",
                resolution=tuple(view["resolutionPx"]),
                location=Vector(view["locationM"]),
                target=Vector(view["targetM"]),
                lens=view["lensMm"],
                sensor_width=view["sensorWidthMm"],
                fps=fps,
            )
            movie = {"path": str(written), "bytes": written.stat().st_size}
            print(f"[skirt] clip {written.name} "
                  f"({written.stat().st_size // 1024} KB)", flush=True)

    return {
        "frames": len(frames),
        "framesPerSecond": fps,
        "prerollFrames": preroll,
        "waistbandErrorMm": round(error * 1000.0, 4),
        "cacheDriftMm": round(drift * 1000.0, 4),
        "rigOnlySecondsPerFrame": round(bare, 3),
        "bakeSeconds": round(sum(solve), 2),
        "prerollSeconds": round(sum(settling), 2),
        "movementSeconds": round(sum(warm), 2),
        "secondsPerFrame": round(sum(warm) / len(warm), 3),
        "worstFrameSeconds": round(max(warm), 3),
        "renderSeconds": round(drawing, 2),
        "sheet": sheet,
        "hem": track,
        "movie": movie,
    }


def parse() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--phase", action="append", default=[])
    parser.add_argument("--no-skirt", action="store_true",
                        help="render the same poses with no garment added")
    parser.add_argument("--animate", action="store_true",
                        help="one continuous cloth bake over the job's frames")
    parser.add_argument("--preroll", type=int, default=PREROLL_FRAMES,
                        help="frames the skirt gets before the movement starts")
    parser.add_argument("--view", default="quarter",
                        help="which camera the sheet and the clip use")
    parser.add_argument("--no-movie", action="store_true",
                        help="write the sheet and skip the clip")
    # ONE VARIABLE PER RUN, AND THE RUN SAYS WHICH ONE.
    #
    # Chasing a look by editing six values between renders produced a worse
    # skirt that could not be attributed to any of them, and three
    # one-variable runs then answered the same question in an afternoon. A
    # value given here appears in the command line and in the receipt, so a
    # comparison of two runs is a comparison of two recorded parameter sets
    # rather than of two memories.
    parser.add_argument("--skirt", action="append", default=[],
                        metavar="KEY=VALUE", help="override one SKIRT value")
    parser.add_argument("--cloth", action="append", default=[],
                        metavar="KEY=VALUE", help="override one CLOTH value")
    return parser.parse_args(argv)


def override(table: dict, settings: list[str], label: str) -> list[str]:
    """Apply KEY=VALUE overrides to a parameter table, and refuse a typo.

    A misspelled key must not pass quietly. An override that lands nowhere
    leaves the run reporting a parameter it never used.
    """
    applied = []
    for setting in settings:
        if "=" not in setting:
            raise SystemExit(f"--{label} wants KEY=VALUE, not {setting!r}")
        key, _, raw = setting.partition("=")
        if key not in table:
            raise SystemExit(
                f"--{label} {key!r} is not a {label} parameter. "
                f"The names are: {', '.join(sorted(table))}"
            )
        was = table[key]
        table[key] = type(was)(int(raw) if isinstance(was, bool) else raw)
        applied.append(f"{key} {was} -> {table[key]}")
    return applied


def main() -> None:
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except (AttributeError, ValueError):  # pragma: no cover
        pass
    args = parse()
    for line in override(SKIRT, args.skirt, "skirt"):
        print(f"[skirt] override {line}", flush=True)
    for line in override(CLOTH, args.cloth, "cloth"):
        print(f"[skirt] override {line}", flush=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    job = json.loads(args.job.read_text(encoding="utf-8"))

    studio = Studio(load_reference_catch_config(args.config))
    studio.add_ball(job["phases"][0]["ball"]["radiusM"])
    rig, human, assets = studio.rig, studio.human, studio.assets

    fabric = make_fabric_material(studio.config.presentation)

    if args.animate:
        baked = animate(studio, job, output, args, fabric)
        receipt = output / "cloth-skirt-bake.json"
        receipt.write_text(json.dumps({
            "movementId": job["movementId"],
            "skirt": SKIRT,
            "cloth": CLOTH,
            "bake": baked,
        }, indent=2), encoding="utf-8")
        print(f"[skirt] receipt {receipt}", flush=True)
        return

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
