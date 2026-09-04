"""Which part of the athlete a vertex belongs to, with no Blender in it.

`body_surface_clearance` answers HOW MANY vertices are inside the ball and HOW
DEEP. It cannot say WHICH, and on 2026-09-04 that was the whole question: the
chest pass's release frame put 150 vertices 17.08 mm inside the ball while every
fingertip on both hands was 31 to 67 mm OUTSIDE it. A count and a depth said
"something is inside" and could not say what, so the finding went to the
movement lane as a number with a hole in it.

A count without a location is half a finding. This closes the other half.

THE MESH IS WEIGHTED TO BONES, so a vertex's region is read from the vertex
group that holds most of its weight — `lowerarm_l` is a forearm, `spine_03` is
a torso. That is a reading of the rig rather than a guess from position, which
matters because a forearm crossing the chest is at chest HEIGHT and would be
called torso by any coordinate rule.

The mapping lives here, apart from Blender, so the rule can be tested. The
Blender side collects (group, gap) pairs and this decides what they mean.
"""

from __future__ import annotations

HAND = "hand"
FOREARM = "forearm"
UPPER_ARM = "upper arm"
TORSO = "torso"
HEAD = "head"
LEG = "leg"
UNKNOWN = "unknown"

FINGERS = ("thumb", "index", "middle", "ring", "pinky")


def region_of(group: str) -> str:
    """The body region a vertex group belongs to.

    Returns UNKNOWN rather than guessing. A group this does not recognise is a
    rig change, and reporting it as `unknown` sends someone to look; folding it
    into the nearest region would hide a rig that had moved underneath.
    """
    if not group:
        return UNKNOWN
    name = group.lower()
    # The finger and hand tests are DISJOINT — `index_01_l` does not start with
    # "hand" and `hand_l` does not start with a digit name — so their order is
    # not load-bearing. An earlier comment here claimed it was, and a mutation
    # that swapped them left the suite green, which is what a claim about code
    # that the code does not depend on looks like.
    if any(name.startswith(f"{digit}_") for digit in FINGERS):
        return HAND
    if name.startswith("hand"):
        return HAND
    if name.startswith("lowerarm"):
        return FOREARM
    if name.startswith("upperarm") or name.startswith("clavicle"):
        return UPPER_ARM
    if name.startswith("spine") or name.startswith("pelvis"):
        return TORSO
    if name.startswith("head") or name.startswith("neck"):
        return HEAD
    if name.startswith("thigh") or name.startswith("calf") or name.startswith("foot"):
        return LEG
    return UNKNOWN


def side_of(group: str) -> str:
    """`l`, `r`, or `` when the group is not sided.

    A left forearm through the ball and a right forearm through it are
    different findings, and "forearm" alone would merge them.
    """
    name = (group or "").lower()
    if name.endswith("_l") or name.endswith(".l"):
        return "l"
    if name.endswith("_r") or name.endswith(".r"):
        return "r"
    return ""


def summarise_inside(samples) -> dict:
    """Group the vertices that are inside the ball by region and side.

    `samples` is (group, gapMetres) per vertex, gap NEGATIVE when inside. Only
    the inside ones are summarised; the rest are the reason the count is not
    the whole mesh.

    The deepest region is named separately because a reader wants one answer
    first. 150 vertices spread over three regions and 150 in one are different
    faults, so both the spread and the leader are reported.
    """
    regions: dict[str, dict] = {}
    groups: dict[str, dict] = {}
    for group, gap in samples:
        if gap >= 0.0:
            continue
        key = region_of(group)
        side = side_of(group)
        label = f"{key} {side}".strip()
        for store, name in ((regions, label), (groups, group)):
            entry = store.setdefault(name, {"vertices": 0, "deepestMm": 0.0})
            entry["vertices"] += 1
            entry["deepestMm"] = min(entry["deepestMm"], gap * 1000.0)

    for store in (regions, groups):
        for entry in store.values():
            entry["deepestMm"] = round(entry["deepestMm"], 3)

    total = sum(entry["vertices"] for entry in regions.values())
    deepest = min(
        (entry["deepestMm"] for entry in regions.values()), default=0.0
    )
    leader = next(
        (name for name, entry in regions.items() if entry["deepestMm"] == deepest),
        None,
    )
    return {
        "verticesInside": total,
        "deepestMm": deepest,
        "deepestRegion": leader,
        "byRegion": dict(sorted(regions.items())),
        # THE EXACT VERTEX GROUP TOO, because "hand" was too coarse for the
        # question actually asked. The movement lane measured the THUMB CHAIN
        # inside the ball on its joint centres while this lane measured the
        # thumb TIP 44 mm outside on the skin. Both can hold: a tip is not a
        # palm and a joint centre is not skin. Only the group name separates a
        # palm vertex from a thumb-web vertex from a finger base.
        "byGroup": dict(sorted(groups.items())),
    }
