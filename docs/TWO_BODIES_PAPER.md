# Two bodies: which of them does a coach's band govern?

Erin grades the engine's solved skeleton, because that is what the bands
measure. She looks at the MPFB athlete, because that is what the manual prints.
They are different bodies.

**This paper is in two halves, per principle 4.** The first half is a
CAPABILITY: what kinds of band can cross between two bodies at all. It is
durable and it belongs with the pipeline. The second half is a RESULT: how far
apart these two particular bodies were on build `2413f9d`. It carries that
build's identity and nothing else.

---

# Part one: capability. What kind of band can cross two bodies

This half does not depend on any build. It follows from what the job carries.

**A band expressed as a DISTANCE cannot cross.** The job transmits everything
normalised except the ball: reach as a fraction of an arm, stance as a fraction
of a leg, the ball's offset in arm lengths. Nothing carries an absolute body
size, deliberately, because the two athletes are not the same size. So a
centimetre measured on one body is not that centimetre on the other, and no
build will make it one.

**A band expressed as a fraction of the body does not cross either, unless the
two bodies have the same proportions.** They do not. The engine's clavicle is
20.4 percent longer relative to its torso than this rig's, which is already
recorded in `KNOWN_ISSUES.md`.

**A band expressed as an ANGLE has a chance**, because an angle is a fact about
a joint rather than about a length. `docs/HANDOFF_RENDERING.md` already states
this rule for ranges of motion: they cross "as a rotation about the anatomical
axis, because it is a fact about the joint rather than a configuration".

**How well an angle crosses is a question for measurement, not for reasoning,
and part two measures it.** The answer is that angles cross better than
distances and still not cleanly.

**What decides it, structurally.** The rendered figure's arms are aimed by a
direction and a fraction of an arm. Its shoulders are placed by a transmitted
displacement its clavicle cannot always reach. So the arm's ANGLES follow the
solve closely, and the arm's POSITIONS inherit every difference in the girdle
and in body size beneath them.

---

# Part two: result, on build `2413f9d`

Read from that build's archived receipts for the rendered side, and solved on
this tree for the engine side.

**Why the two sides are comparable.** All eleven job files on this tree are
byte-identical to the `jobSha256` each receipt recorded, so the solve here is
the solve those figures were rendered from. That is checked, not assumed.

## A correction to this lane's own number, before anything else

This lane reported 36.43 cm on the engine against 32.02 on the rendered
athlete, a gap of 4.41 cm, and called it a same-phase comparison. **It was
not.** 36.43 is a mean over six drills from `COACH_MORNING_2026-09.md`, with a
spread of 28.90 to 40.37, measured on `02b25cd`. 32.02 is one phase of one drill
on `2413f9d`. A mean against a single phase, across two builds, and the mean's
spread is wider than the gap it reported.

**The matched figure is 5.66 cm.** The finding survived. The number did not.

## Distances

Five drills whose both-hands phase is named `contact`: `deflect_high`,
`hooks_jump_pull_in`, `two_hand_catch_chest`, `two_hand_snatch_pull_in`,
`two_hand_snatch_straight_back`.

    elbows, centimetres        engine 38.73      rendered 33.07    narrower by 5.66
    elbows, shoulder spans     engine  1.022     rendered  1.130   WIDER by 0.109

**Both are true at once.** The rendered elbows are absolutely narrower and
relatively wider, because her shoulders are narrow while her arms are aimed by a
direction and a fraction of an arm that do not shrink with them.

Across all 48 phases the ratio difference runs −0.213 to +0.242 for the elbows
and −0.178 to +0.126 for the wrists. It is not a constant, so no restatement of
a distance band makes it transfer.

**This is NOT the page's six-drill population.** That six was chosen before
`bounce_pass` and `one_hand_high_pass` existed. This lane measured five, named
them, and does not claim a match.

**The shoulders row reads 0.000 by construction**, because the shoulder span is
the divisor. It is not evidence of agreement.

## Angles, by one formula applied to both bodies

96 readings, both arms, every graded phase.

    shoulder elevation   engine minus rendered   -13.27 to +2.27 deg, median -3.98
    elbow flexion        engine minus rendered    +0.06 to +7.27 deg, median +2.81

Both trunks stand within 2.39 degrees of vertical at every phase, so world-down
is a fair reference for both, and 2.39 degrees is the error that choice admits.
Within that allowance sit 27 of 96 elevation readings and 47 of 96 flexion
readings.

**So angles cross better than distances and not cleanly.** Elbow flexion is the
closest quantity in this paper. Shoulder elevation is the worst.

## The consequence for item 11, which nobody has raised

The morning asks Erin to set **a shoulder elevation floor at contact, currently
50.0, which the low ball misses by 0.05**.

The two bodies disagree on shoulder elevation by up to **13.27 degrees**, and by
a median of 3.98. **The margin she is asked to rule on is 0.05 degrees.** A
floor met on the skeleton by 0.05 can be missed on the printed figure by
several degrees, and the sign of the disagreement is not constant.

## A hypothesis measured away

The renderer never rotates the spine: `pose_stance` translates the pelvis and
rotates the legs, and `pose_girdle` rotates the clavicles. So the rendered trunk
stands at one angle on every phase, and a leaning engine athlete would have been
a large unmeasured disagreement.

**It is not one.** The engine's own trunk leans 0.11 to 2.39 degrees from
vertical across all 48 phases. Most upright is `overhead_pass/lift` at 0.11 and
most leaned is `chest_pass/follow_through` at 2.39. The renderer's fixed trunk
costs at most 2.39 degrees, and that is the allowance used above.

## A flag, not a finding

On this build and this five-drill population the ENGINE's own elbow mean is
38.73 cm against the manual's 38.6, a gap of 0.13 cm. The page states the gap at
31.3 is 2.17 cm, from 36.43 on `02b25cd` over six drills.

**This lane claims nothing except that the number the question rests on has
moved.** The build differs, the population differs, and the dial is the movement
lane's. It should be re-measured on `2413f9d` before Erin is asked to close a
gap that may not be the size the question describes.

## What is still not measured

- The ball speeds, item 3. They are not a body quantity and no two-body
  disagreement exists for them.
- The finger closing speed, item 4. The receipts carry one pose per phase, so a
  rate needs frames the archive does not hold.
- The release-hand angles. They wait on the movement lane's flick model.
- Anything below the hips. Nothing below the hips may be presented as a graded
  value on this rig.

## Instruments

    scripts/two_bodies_compare.py     the distances, raw and per shoulder span
    scripts/two_bodies_angles.py      shoulder elevation, elbow flexion, trunk lean

Both solve the engine side on this tree and read the rendered side from the
archive, and both name the build they read.
