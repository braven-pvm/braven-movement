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
