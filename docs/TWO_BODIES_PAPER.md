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
the solve those figures were rendered from.

**That sentence used to be a claim and is now a guard.** It was true when each
instrument was written and nothing read it afterwards, so a job file changing
under a lane would have left every number below comparing two different solves,
silently, with this paper still asserting they agree.
`scripts/archive_agreement.py` now REFUSES rather than reports, and all three
instruments call it before they print a row.

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

## Item 6: the ready pose. The figure shows half of what the question asks about

The morning asks Erin whether 20 cm between the wrists is a shown arm span or a
pair of hands held together. Wrist to wrist at the first frame:

    drill                          engine  rendered    gap   eng/span  ren/span
    two_hand_catch_chest            20.10     11.41   8.69      0.511     0.392
    two_hand_snatch_pull_in         20.08     11.40   8.68      0.511     0.391
    two_hand_snatch_straight_back   20.08     11.40   8.68      0.511     0.391
    double_foot_landing             19.91     11.37   8.54      0.508     0.390
    hooks_jump_pull_in              19.83     11.35   8.49      0.506     0.389
    deflect_high                    18.29     13.76   4.53      0.527     0.476

**The number in the question is not the number on the page.** She is asked about
20 cm and shown 11.4 cm. That is 43 percent of the quantity removed, and it is
not a scale difference, because as a fraction of each body's own shoulder span it
is still 0.511 against 0.392.

**The disagreement pushes the answer one way.** 11.4 cm reads as a pair of hands
held together far more plainly than 20 cm does. Whatever Erin rules, she rules it
on a figure that argues for one of the two answers.

### The rendered figure invents a grouping the skeleton does not have

The three passes are not in the morning's table. They belong in this comparison,
because a coach sees the whole library:

    bounce_pass                     21.41     20.91   0.50      0.542     0.720
    chest_pass                      21.41     20.92   0.50      0.542     0.720
    overhead_pass                   21.41     20.92   0.50      0.542     0.720

On the engine, all nine sit between 18.29 and 21.41, a spread of 3.12 cm. On the
rendered figure they split in two: the passes at 20.9 and the catches at 11.4, a
spread of 9.57 cm. **A coach turning the pages sees two families. The skeleton
has one.**

### The rank order inverts at the top

`deflect_high` is the NARROWEST ready pose on the engine at 18.29 cm and the
WIDEST of the six on the rendered figure at 13.76 cm. It is 1.54 cm below its
neighbour on one body and 2.35 cm above it on the other, against a spread of
0.06 cm among the other five. **This is an inversion and not a tie broken two
ways.** A coach ranking the drills by shown arm span would rank them differently
on the two bodies.

## Item 5, the second hand: the quantity crosses, the question does not

**THE AGREEMENT IS BETTER ON BOTH DRILLS THAN THIS LANE FIRST PUBLISHED ON ONE.**
Every gap is positive and between 0.56 and 2.20 cm, on both join drills.

    one_hand_snatch_to_other_hand    engine  rendered    gap
    ready f0                          12.02     11.08   0.94
    reach f34                         12.01     11.07   0.94
    contact f48                       12.02     11.06   0.96
    join f70                          20.23     18.10   2.13
    pull_in f97                       12.07     10.52   1.55

    hooks_outside_hand               engine  rendered    gap
    facing_away f0                    12.08     11.52   0.56
    contact f48                       12.35     11.57   0.78
    gather f72                        19.47     17.27   2.20
    pull_in f97                       12.07     10.48   1.60

**This is the closest agreement in the paper.** Item 5's quantity crosses.

### The axis, and how it was settled

The quantity is the AHEAD component from the shoulder midpoint, **in the
athlete's own frame**. Four reasons, in the order they carry weight:

1. **The cue is stated in body terms.** Erin's note says the other hand should
   not go away from the CENTRE OF BODY towards the ball, and the ledger says
   AHEAD OF HER SHOULDERS. An instrument must measure the quantity the cue names.
2. **A world number adds shoulder rotation to hand travel.** `hooks_outside_hand`
   turns, and the turn unwinds from 48.22 degrees at the first frame to 21.76 at
   contact to 4.06 at the last. A number carrying that rotation cannot answer a
   question about the hand.
3. **The engine's own `ahead` field is body-relative**, at
   `motion_track.py:426`, `ball_track.py:368` and, inverted,
   `possession.py:275`. There is no world-ahead anywhere in the engine.
4. **Reproduction settles nothing here**, and this lane published a wrong axis by
   trusting it. Refer to the record below.

### The question still does not cross, and that belongs in part one

It asks about the TRAVEL, and the travel needs the frame where the hand is
furthest out. The engine puts those at frames 58 and 60 and neither is a phase
frame, so no rendered figure exists at the moment the question is about.

    travel, engine only    snatch 13.96 cm    hooks 12.71 cm

**A CLIP WOULD NOT SETTLE IT, and the running order plans one.** `animation` is
null on every archived receipt, and the animate path records frame counts and
file hashes, never a per-frame joint position.

### What this lane published on the wrong axis, and withdrew

**EVERYTHING MEASURED ON THE WORLD AXIS IS WITHDRAWN. EVERYTHING ON THE BODY
AXIS OR AXIS-FREE STANDS.** That is the whole episode in one line.

    withdrawn   "item 5's conclusion reverses"
    withdrawn   "the two drills are not the same shape"
    withdrawn   "the hooks drill has no distinct ramp start"
    withdrawn   the travel figure 14.48 cm and every world-axis ramp number
    withdrawn   "the ledger's 35.6 cm is a unit conversion of the engine's key"
    stands      the agenda's hooks row is from the struck pose, 10.73 cm off
    stands      every item 6 row, because a 3D distance has no axis

**How the wrong axis was chosen.** Four components were tried on
`one_hand_snatch_to_other_hand` and the one that reproduced the recorded numbers
was kept. **That athlete is square — 0.07 degrees of turn at contact — so two of
the four are the same axis there and agreed to 0.01 cm.** The winning margin was
0.17 against 0.18, inside the noise, and it was published as a choice.

**A test with no power to separate two answers looks exactly like a test that
chose between them.** The check is to ask what the instrument would report if the
opposite were true.

**And a second false settlement was refused rather than published.** The ledger's
35.6 cm can be fitted to 0.13 cm by choosing one of two scales and one of four
spine joints. **Eight combinations will produce a near-miss by chance**, so the
fit is not evidence. Count the free choices before believing one.

## What the running order makes of these two items

`docs/COACH_MORNING_RUNNING_ORDER.md` arrived on main on 2026-09-09 and plans
both items. It changes what the two measurements above mean.

**Item 6 is planned as a picture she accepts or rejects**, drawn as "a still at
the ready frame", and the still is on the page already. So the disagreement is
not academic. The text of the question says 20 cm and the picture beside it shows
11.4 cm, and she is asked to rule on the picture.

**Item 5 is planned as "the 14 cm figure and a clip".** A clip does NOT settle
the two-body question, and a reader would reasonably assume it does.

    every archived receipt          "animation": null
    what the animate path records   frame count, rate, and the file hashes

`blender_movement_render.py` poses the rig at every exported frame under
`--animate`, and writes counts and file hashes for the result. It records no
per-frame joint position. So a clip would DRAW the peak and record nothing about
it, and the comparison would still be impossible afterwards.

**Two things would make it measurable, and both are somebody else's.** The job
could carry a phase at the peak frame, which is the movement lane's, or the
animate path could record per-frame arms, which is this lane's renderer and a
widening of the receipt. This lane proposes neither here. It records that the
planned artefact does not answer the question, so that nobody discovers it after
the clip is made.

## Two rows of the coach morning were read on the struck pose

Item 7 is STRUCK because `hooks_outside_hand` has two solved poses about 33
degrees apart at the first frame. On `ac240b2` the agenda records 48.22 degrees
as the corrected pose and 15.44 as the pose the shipped parameter set reached,
and it states that items 1 to 9 were re-measured on the tree that gave 15.44.

**Both bodies now hold the corrected pose.** Measured on `2413f9d`, as the turn
of the shoulder line at the first frame, the engine gives 48.22 degrees and the
rendered figure 45.48. So two rows measured on the other pose are still in the
agenda, unmarked.

The quantity here is the shoulder line, not the feet. Nothing below the hips is
presented as a graded value anywhere in this paper.

On `ac240b2`, as the agenda states them:

    item 6, hooks_outside_hand    45.68 cm wrist to wrist
    item 5, hooks_outside_hand    3.43 cm out to 14.33, back to 3.48, travel 10.90

On `2413f9d`, this tree and the rendered library:

    item 6, hooks_outside_hand    40.36 cm wrist to wrist
    item 5, hooks_outside_hand    7.45 cm out to 21.93, back to 11.28, travel 14.48

**The engine side of item 6 reproduces exactly on seven of its eight rows.** The
eighth is this drill. That is the pattern the artefact predicts, and it is why
the cause is named rather than guessed.

**Item 5's conclusion reverses.** The agenda says the second drill "sits closer
in". Its `ac240b2` figures are a travel of 10.90 cm on the second drill against
14.12 on the first.
On `2413f9d` the second drill travels 14.48 cm and the first 13.94.
**The two drills agree, and the second is the wider of the two.** So the question of whether about 14 cm of
travel is too much applies equally to both, where the agenda presents one of them
as the milder case.

**This lane does not change the agenda.** To strike or amend an item is the
orchestrator's, and the drill is the movement lane's. This is the measurement,
with the instrument beside it.

## What is still not measured

- The travel of the second hand, item 5, on the rendered figure. The peak frame
  is not a phase frame and the archive holds no pose there. Every phase frame IS
  measured, above.
- The ball speeds, item 3. They are not a body quantity and no two-body
  disagreement exists for them.
- The finger closing speed, item 4. The receipts carry one pose per phase, so a
  rate needs frames the archive does not hold.
- The release-hand angles. They wait on the movement lane's flick model.
- Anything below the hips. Nothing below the hips may be presented as a graded
  value on this rig.

## Instruments

    scripts/archive_agreement.py         REFUSES unless this tree still solves
                                         what the archived figures were drawn from
    scripts/two_bodies_compare.py        the distances, raw and per shoulder span
    scripts/two_bodies_angles.py         shoulder elevation, elbow flexion, trunk lean
    scripts/two_bodies_ready_and_join.py items 6 and 5, and the turn at the first frame

Both solve the engine side on this tree and read the rendered side from the
archive, and both name the build they read.
