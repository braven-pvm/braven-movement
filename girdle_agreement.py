"""Does the rendered shoulder girdle agree with the one the job transmits?

THE BALL IS ANCHORED TO A LANDMARK THE JOB DID NOT SEND. `pose_phase` places
it at `shoulders + fromShouldersInArms * arm`, where `shoulders` is THIS rig's
midpoint. Every other term is transmitted, so the ball's error was the
midpoint's error, one for one. On 2026-09-04 this rig held one girdle pose for
all 18 graded phases of four drills (42.7681 cm above the pelvis, range
0.0000) while the engine's travelled 7.40 cm inside the overhead pass alone.
Three of the 18 figures passed a 1 cm rule, and the three that passed were the
three neutral-girdle phases.

The job now carries both shoulder positions. This is the guard that says the
renderer actually USED them. It is a comparison, not a correction: it never
moves a bone, it refuses a frame.

WHY NOT `== 0.0`. The job writes six decimals in metres, so a transmitted
position is already up to half a micron from the solved one before this rig
touches it. A guard demanding an exact zero would fail on the rounding and be
switched off, which is worse than no guard. The tolerance below is ten times
the rounding bound and still a thousand times smaller than the smallest error
anyone cares about.
"""

from __future__ import annotations

# The job writes positions to six decimal places in metres.
ROUNDING_M = 1e-6
# Ten times that bound. The smallest error this pack cares about is 1 cm, so
# this sits 1000x below it: nothing real can hide underneath.
TOLERANCE_M = 1e-5

UNAVAILABLE = "unavailable"
AGREES = "agrees"
DISAGREES = "disagrees"


# THIS RIG'S REST TORSO, the divisor for a transmitted offset. It is the
# MAGNITUDE |rest shoulder midpoint - rest pelvis|, 42.7689 cm. The number this
# lane published first, 42.7681, is the VERTICAL COMPONENT of the same span.
# They agree to 0.0008 cm here only because this torso is almost purely
# vertical at rest. On another body they need not, so the divisor is the
# magnitude and never the component.
REST_TORSO_M = 0.427689


def resolve(displacement, rest_span, rest_torso: float = REST_TORSO_M):
    """Scale a transmitted girdle displacement onto this body, PELVIS-RELATIVE.

    `rest_span` is (rest shoulder - rest PELVIS) on this body, not an absolute
    rest shoulder position, and the return is a span too. Both sides of the
    engine's subtraction are pelvis-relative, so both sides of this one must be.
    The solved root is never at its rest position, 8.4 cm off at every ready
    phase, so applying a displacement to an absolute rest position would carry
    the root's own motion into the girdle. Add the POSED pelvis afterwards with
    `shoulder_position`.

    A displacement is sent rather than a position because a position cannot
    cross between two bodies. Resolving the engine's POSITIONS onto this rig
    put zero of 48 phases under the 1 cm rule, and `chest_pass/ready` read
    2.488 cm at a phase where both bodies sit at their neutral girdle and
    nothing is wrong. A divisor SCALES and does not TRANSLATE, so no scalar
    removes a landmark or a posture difference. A displacement cancels every
    constant and reads zero where nothing is wrong.

    The reference is the REST POSE and not a drill's neutral phase, because the
    rest pose is the only reference both sides compute without being told.

    The divisor is a TORSO length. Arm lengths were proposed by this lane and
    refuted by measurement: the two rigs' arm-to-torso ratios differ by about 5
    percent, which would have failed the rule at the neutral phase the fix
    exists to protect. Metres are worse, because every length in the job is
    normalised except `ball.radiusM`, which is absolute only because a real
    netball is one physical size on every body.
    """
    return tuple(rest + step * rest_torso
                 for rest, step in zip(rest_span, displacement))


def shoulder_position(displacement, rest_span, posed_pelvis,
                      rest_torso: float = REST_TORSO_M):
    """Where the shoulder goes on a POSED body, in world coordinates.

    The span is resolved first and the POSED pelvis is added last. Adding the
    rest pelvis instead would hold the girdle to a root that has moved.
    """
    return tuple(pelvis + span for pelvis, span
                 in zip(posed_pelvis, resolve(displacement, rest_span,
                                              rest_torso)))


def midpoint(left, right):
    """The point the ball is placed from."""
    return tuple((a + b) / 2.0 for a, b in zip(left, right))


def agreement(rendered, transmitted, tolerance: float = TOLERANCE_M) -> dict:
    """Compare a rendered midpoint against the transmitted one.

    BOTH POINTS MUST BE ON THE SAME BODY. Pass the transmitted offset through
    `resolve` first. Comparing this rig's midpoint against another body's
    absolute position can never read zero, because the bodies differ, and a
    guard that can never pass is a guard that gets switched off.

    `transmitted` of None means the job did not carry it. That is reported as
    UNAVAILABLE and never as agreement: a frame nobody could check must not
    read the same as a frame that passed. The whole finding this guard exists
    for was a missing field behaving like a satisfied one.

    Per-axis offsets are reported beside the magnitude because the engine's
    first measurement was VERTICAL ONLY, and a fore-and-aft error of the same
    size would have been invisible in a single distance.
    """
    if transmitted is None:
        return {
            "verdict": UNAVAILABLE,
            "offsetMm": None,
            "perAxisMm": None,
            "toleranceMm": tolerance * 1000.0,
        }

    per_axis = [(r - t) * 1000.0 for r, t in zip(rendered, transmitted)]
    offset = sum(component ** 2 for component in per_axis) ** 0.5
    return {
        "verdict": AGREES if offset <= tolerance * 1000.0 else DISAGREES,
        "offsetMm": offset,
        "perAxisMm": per_axis,
        "toleranceMm": tolerance * 1000.0,
    }


def refuse_unless_agreed(report: dict, label: str) -> None:
    """Raise unless the girdle agreed. UNAVAILABLE raises too.

    A renderer that carried on past a disagreement would put a figure in front
    of a coach with the ball somewhere no solve placed it, which is the fault
    this whole guard was written for.
    """
    if report["verdict"] == AGREES:
        return
    if report["verdict"] == UNAVAILABLE:
        raise ValueError(
            f"{label}: the job carried no shoulder positions, so the ball's "
            f"anchor cannot be checked. Refusing the frame rather than "
            f"rendering an unverifiable one."
        )
    raise ValueError(
        f"{label}: the rendered shoulder midpoint is {report['offsetMm']:.4f} "
        f"mm from the transmitted one, past the "
        f"{report['toleranceMm']:.4f} mm tolerance. Per axis: "
        f"{[round(v, 4) for v in report['perAxisMm']]}."
    )
