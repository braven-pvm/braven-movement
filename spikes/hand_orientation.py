"""Hand orientation, read back from the solved skeleton. Report-only.

Erin Burger's blind review (docs/COACH_REVIEW_2026-08-30.md, section 3,
"supports neither") left two contact cues the engine could not grade because no
measure reads hand orientation: "Thumbs shouldn't be up" on the chest catch and
"Fingers up, thumbs in the middle" on the jump hooks. The engine measured trunk
turn, trunk lean, elbow flexion, shoulder elevation, knee flexion and foot
height. A thumb's direction was invisible to it. This module is the eyes.

Nothing here grades. Every value is reported with no band and no verdict,
because bands are coaching content and no coach has seen these numbers yet.
Erin and Marius set bands from the reported values, or decide not to.

The three measures, defined before they were implemented
--------------------------------------------------------

Every measure is an angle between two vectors whose endpoints are solved joint
centres, in the style of segment_measures.py: no synthesised landmark, no Euler
sequence, no plane normal to flip. Every one names its space and its
convention, because the elbow convention's history in this repository is a
warning about leaving either implicit.

**1. thumbUpDegrees** (one per hand: leftThumbUpDegrees, rightThumbUpDegrees)

    The angle between the thumb ray and world up.

    - Thumb ray: from the thumb base joint (``{side}_thumb1``) to the thumb
      tip joint (``{side}_thumb3``), world positions from the solved skeleton.
      Base to tip. The reversed ray reads 180 minus the truth, which is why the
      direction is named here and proven by a mutation in the tests.
    - Space: world. MHR is Y up, centimetres. The reference is
      WORLD_UP = (0, 1, 0), the same constant movement_engine.py measures
      trunk lean against.
    - Convention: 0 means the thumb points straight up, the hitch-hiker's
      thumbs-up Erin's chest-catch cue bans. 90 means level. 180 means
      straight down. The range is 0 to 180; there is no sign, because the
      measure is a cone angle about up, not a rotation about an axis.
    - Why world up and not her frame's up: "thumbs up" is a gravity word - a
      coach watching a leaning athlete still means the sky. The two references
      differ by exactly the trunk lean, which at the contacts Erin annotated
      is about 2 degrees, under the 5 degree band floor. The choice is stated
      so a reader knows which was made and by how much it could matter.
    - Worked example: a thumb ray of (3, 4, 0) cm has length 5 and its dot
      with (0, 1, 0) is 4, so cos(theta) = 4/5 and thumbUpDegrees = 36.87.

**2. fingerUpDegrees** (one per hand)

    The angle between the hand's finger direction and world up.

    - Finger direction: from the wrist joint (``{side}_wrist``) to the middle
      knuckle (``{side}_middle1``), world positions from the solved skeleton.
      This is the hand's long axis, the same pair grip.py builds its e1 from.
      It is chosen over knuckle-to-fingertip deliberately: fingers curled
      around a caught ball bend at the knuckles, so a tip direction would
      conflate curl with orientation. "Fingers up" is about which way the hand
      points.
    - Space: world, reference WORLD_UP, exactly as measure 1.
    - Convention: 0 means the fingers point straight up, which is Erin's
      jump-hooks cue "fingers up". 90 means level. 180 means straight down.
      Range 0 to 180, no sign.
    - Worked example: wrist at (0, 90, 10) and middle knuckle at (0, 94, 7)
      give a ray of (0, 4, -3), length 5, dot with up 4, so
      fingerUpDegrees = 36.87.

**3. thumbToBallDegrees** (one per hand)

    The angle between the thumb ray and the direction from the thumb base to
    the centre of the ball.

    - Thumb ray: as measure 1, base to tip.
    - Ball centre: the possession model's ball centre on the same frame
      (``frame.centre``), world centimetres. Both vectors live in world space;
      the angle between them is frame-invariant.
    - Convention: 0 means the thumb points straight at the middle of the
      ball, which is the geometric reading of "thumbs in the middle": on a
      two-handed catch the hands take the sides of the ball and both thumbs
      point inward, meeting behind its middle. 90 means the thumb runs along
      the ball's surface. 180 means it points away. Range 0 to 180, no sign.
    - Worked example: thumb base (10, 100, 0), tip (13, 104, 0), ball centre
      (20, 100, 0). Thumb ray (3, 4, 0), base-to-centre (10, 0, 0),
      cos(theta) = 30 / (5 * 10) = 0.6, thumbToBallDegrees = 53.13.

What was evaluated and not chosen
---------------------------------

- The palm normal (grip.reconstruct gives it). Rejected as the carrier for
  these two cues: Erin's words name thumbs and fingers, and at contact the
  palm normal is what the authored grip already pins (every palm faces the
  ball centre by construction, grip.contacts), so it can barely see a fault
  the thumb chain itself carries. It stays available for a later cue that is
  actually about the palm.
- Fingertip direction relative to the ball. Rejected for the curl conflation
  named under measure 2. The ball centre survives as the reference for
  measure 3, where "the middle" genuinely is the ball's middle.
- Her frame's up as the reference. Rejected for the gravity argument under
  measure 1, with the size of the difference stated.

How the values reach a receipt
------------------------------

build_library.py adds a ``handOrientation`` section to each possession
receipt: per coaching phase, per hand, the three measures as rows shaped like
coaching rows - ``{measure, measured, band, verdict, cue}`` - with ``band``
null and ``verdict`` "reported", which is the marker for a value published for
coaches to read rather than graded. The section is deliberately NOT inside
``coaching.phases``: every consumer of coaching rows assumes a two-number band
and counts rows into the grading score, and a report-only row must change
neither.

Two instruments
---------------

Nothing certifies on one instrument. This module is the primary read, from the
solved joint centres, using segment_measures.angle_between_degrees (an acos
formulation). hand_orientation_crosscheck.py is the second: it recomputes
every reported row from the coach animations export
(poc-output/coach/animations.json, a separate pipeline with its own joint
extraction and millimetre rounding) using an atan2 formulation, and fails
loudly when the two disagree beyond the quantisation budget. Agreement is
reported, not assumed.
"""

from __future__ import annotations

from segment_measures import SegmentMeasureError, angle_between_degrees

Vector = tuple[float, float, float]

# The same up the trunk lean is measured against. movement_engine.py owns the
# constant but also imports pymomentum, which this module must not need, so the
# value is restated here and test_hand_orientation.py asserts the two are equal
# whenever the solver is present. MHR is Y up.
WORLD_UP: Vector = (0.0, 1.0, 0.0)

# The verdict that marks a row as published rather than graded. Coaching rows
# say below, within or above; a reported row says only what was measured.
REPORTED = "reported"

# What each measure's zero and ninety mean, carried inside the receipt so a
# reader of the row does not need this file open to read the number.
CONVENTIONS = {
    "ThumbUpDegrees": (
        "thumb base to thumb tip, against world up: 0 is a thumb pointing "
        "straight up, 90 is level, 180 is straight down"
    ),
    "FingerUpDegrees": (
        "wrist to middle knuckle, against world up: 0 is the fingers pointing "
        "straight up, 90 is level, 180 is straight down"
    ),
    "ThumbToBallDegrees": (
        "thumb base to thumb tip, against the direction to the ball centre: "
        "0 is a thumb pointing at the middle of the ball, 90 is along its "
        "surface, 180 is away from it"
    ),
}


def _as_vector(point) -> Vector:
    return (float(point[0]), float(point[1]), float(point[2]))


def _ray(start, end, name: str) -> Vector:
    first = _as_vector(start)
    second = _as_vector(end)
    ray = (second[0] - first[0], second[1] - first[1], second[2] - first[2])
    if ray == (0.0, 0.0, 0.0):
        raise SegmentMeasureError(f"{name} has coincident endpoints")
    return ray


def thumb_up_degrees(*, thumb_base, thumb_tip, up: Vector = WORLD_UP) -> float:
    """Measure 1. Space: world. 0 is thumbs-up, 90 level, 180 down."""
    return angle_between_degrees(
        _ray(thumb_base, thumb_tip, "thumb ray"), up, "thumb against up"
    )


def finger_up_degrees(*, wrist, middle_knuckle, up: Vector = WORLD_UP) -> float:
    """Measure 2. Space: world. 0 is fingers-up, 90 level, 180 down."""
    return angle_between_degrees(
        _ray(wrist, middle_knuckle, "finger direction"), up, "fingers against up"
    )


def thumb_to_ball_degrees(*, thumb_base, thumb_tip, ball_centre) -> float:
    """Measure 3. Space: world, frame-invariant. 0 points at the ball's middle."""
    return angle_between_degrees(
        _ray(thumb_base, thumb_tip, "thumb ray"),
        _ray(thumb_base, ball_centre, "thumb base to ball centre"),
        "thumb against the ball centre",
    )


def measure_hand(points, index: dict[str, int], side: str, ball_centre) -> dict:
    """All three measures for one hand, from one solved frame's joint centres.

    ``points`` is the solved skeleton's world joint positions in centimetres,
    ``index`` maps joint names to rows, ``side`` is "l" or "r", and
    ``ball_centre`` is the possession model's ball centre for the same frame.
    There is no per-side special case anywhere below; the measures are
    side-agnostic by construction, and the tests hold them to that.
    """
    thumb_base = points[index[f"{side}_thumb1"]]
    thumb_tip = points[index[f"{side}_thumb3"]]
    return {
        "ThumbUpDegrees": thumb_up_degrees(
            thumb_base=thumb_base, thumb_tip=thumb_tip
        ),
        "FingerUpDegrees": finger_up_degrees(
            wrist=points[index[f"{side}_wrist"]],
            middle_knuckle=points[index[f"{side}_middle1"]],
        ),
        "ThumbToBallDegrees": thumb_to_ball_degrees(
            thumb_base=thumb_base, thumb_tip=thumb_tip, ball_centre=ball_centre
        ),
    }


def receipt_rows(points, index: dict[str, int], ball_centre) -> list[dict]:
    """Both hands of one frame, as report-only rows shaped like coaching rows.

    ``band`` is null and ``verdict`` is "reported": these rows grade nothing.
    The ``cue`` slot carries the measure's own convention, so the row reads
    without this file open. Left before right, measures in definition order,
    so receipts diff cleanly between builds.
    """
    rows = []
    for side, prefix in (("l", "left"), ("r", "right")):
        measured = measure_hand(points, index, side, ball_centre)
        for suffix, value in measured.items():
            rows.append(
                {
                    "measure": f"{prefix}{suffix}",
                    "measured": round(value, 2),
                    "band": None,
                    "verdict": REPORTED,
                    "cue": CONVENTIONS[suffix],
                }
            )
    return rows


def receipt_section(result: dict, definition) -> dict:
    """The handOrientation section of one movement's receipt.

    ``result`` is what possession_solve.solve_movement returned; ``definition``
    is the movement's coaching definition. Each coaching phase reads the frame
    the grading reads: round(atPhase * (frames - 1)), the same formula
    MovementDefinition.assess uses, so a reported value and a graded value at
    the same phase come from the same solved frame.
    """
    held = result["possession"]
    points = result["points"]
    index = result["index"]
    last = len(points) - 1
    phases = {}
    for phase in definition.phases:
        number = round(phase.at_phase * last)
        frame = held.frames[number]
        phases[phase.name] = {
            "frame": number,
            "holdingTheBall": bool(frame.holding),
            "rows": receipt_rows(points[number], index, frame.centre),
        }
    return {
        "status": "report-only",
        "note": (
            "no band and no verdict: bands are coaching content, and no coach "
            "has read these numbers yet. thumbToBallDegrees is a grip "
            "statement only on phases where she holds the ball; elsewhere it "
            "reads the hand against a ball still in flight."
        ),
        "phases": phases,
    }
