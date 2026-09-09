# Two bodies: the rendering lane's pack

Everything here answers one question: **which body does a coach's band govern?**
Erin grades the engine's solved skeleton, because that is what the bands measure.
She looks at the MPFB athlete, because that is what the manual prints.

Measured on `2413f9d`, eleven drills, 48 graded phases, both bodies.

**WHY THE TWO SIDES ARE COMPARABLE, AND IT IS NOW A GUARD RATHER THAN A CLAIM.**
All eleven job files on this tree are byte-identical to the `jobSha256` their
receipt recorded, so the solve here IS the solve those figures were rendered
from. `scripts/archive_agreement.py` refuses rather than reports, and all three
instruments call it before printing a row.

---

## 1. The capability answer, which depends on no build

Split from the result per `.remember/PRINCIPLES.md` principle 4.

**A band expressed as a DISTANCE cannot cross.** The job transmits everything
normalised except the ball, deliberately, because the two athletes are not the
same size. No build will make a centimetre on one body that centimetre on the
other.

**A band expressed as a fraction of the body does not cross either**, unless the
proportions match, and they do not: the engine's clavicle is 20.4 percent longer
relative to its torso.

**A band expressed as an ANGLE has a chance**, because an angle is a fact about a
joint. `docs/HANDOFF_RENDERING.md` already states that rule for ranges of motion.

**How well is a question for measurement.** Sections 2 and 3 measure it. Angles
cross better than distances and still not cleanly.

## 2. The clearest single row, and both halves are true

    elbows, centimetres        engine 38.73     rendered 33.07    NARROWER by 5.66
    elbows, shoulder spans     engine  1.022    rendered  1.130   WIDER by 0.109

The rendered elbows are absolutely narrower and relatively wider at the same
time. Her shoulders are narrow, and her arms are aimed by a direction and a
fraction of an arm that do not shrink with them.

Across all 48 phases the ratio difference runs −0.213 to +0.242 for the elbows
and −0.178 to +0.126 for the wrists. **It is not a constant, so no restatement of
a distance band makes it transfer.**

**A CORRECTION TO THIS LANE'S OWN PUBLISHED NUMBER.** This lane reported 4.41 cm
and called it a same-phase comparison. It was not. 36.43 is a mean over six
drills on `02b25cd`, spread 28.90 to 40.37; 32.02 is one phase of one drill on
`2413f9d`. The mean's spread was wider than the gap it reported. **The matched
figure is 5.66 cm. The finding survived and the number did not.**

## 3. Angles, by one formula on both bodies

96 readings, both arms, every graded phase.

    shoulder elevation   engine minus rendered   -13.27 to +2.27 deg, median -3.98
    elbow flexion        engine minus rendered    +0.06 to +7.27 deg, median +2.81

Within the 2.39 degree allowance sit 27 of 96 elevation readings and 47 of 96
flexion readings. Elbow flexion is the closest quantity in this pack. Shoulder
elevation is the worst.

**THE ALLOWANCE IS MEASURED, NOT ASSUMED.** The renderer never rotates the spine,
so a leaning engine athlete would have been a large silent disagreement. It is
not one: the engine's trunk leans 0.11 to 2.39 degrees over all 48 phases. That
2.39 is the allowance, and the hypothesis is measured away rather than left in
the pack as a worry.

## 4. The consequence for item 11, which nobody had raised

The morning asks Erin to set **a shoulder elevation floor at contact, currently
50.0, which the low ball misses by 0.05**.

**The two bodies disagree on that same quantity by up to 13.27 degrees**, by a
median of 3.98, and the sign is not constant. A floor met on the skeleton by 0.05
can be missed on the printed figure by several degrees.

This is a fact about the margin she is asked to set. **It is not a proposal about
what to set it to.**

## 5. Item 6, the ready pose: the figure shows half of what the question asks

    drill                          engine  rendered    gap   eng/span  ren/span
    two_hand_catch_chest            20.10     11.41   8.69      0.511     0.392
    two_hand_snatch_pull_in         20.08     11.40   8.68      0.511     0.391
    two_hand_snatch_straight_back   20.08     11.40   8.68      0.511     0.391
    double_foot_landing             19.91     11.37   8.54      0.508     0.390
    hooks_jump_pull_in              19.83     11.35   8.49      0.506     0.389
    deflect_high                    18.29     13.76   4.53      0.527     0.476

**She is asked about 20 cm and shown 11.4 cm**, and it is not a scale difference,
because as a fraction of each body's own shoulder span it is 0.511 against 0.392.
The running order plans this item as a picture she accepts or rejects, so the
disagreement decides the answer rather than decorating it.

**11.4 cm reads as a pair of hands held together far more plainly than 20 cm
does. That is an observation for the room and not a recommendation.**

**THE RENDERED LIBRARY SHOWS TWO FAMILIES WHERE THE SKELETON HAS ONE.** The three
passes render at 20.9 and the catches at 11.4, a spread of 9.57 cm. On the engine
all nine sit between 18.29 and 21.41, a spread of 3.12.

**AND THE RANK ORDER INVERTS AT THE TOP.** `deflect_high` is the narrowest ready
pose on the engine and the widest of the six on the rendered figure: 1.54 cm
below its neighbour on one body and 2.35 above it on the other, against 0.06 cm
of spread among the other five. **An inversion is not a tie broken two ways.**

## 6. Item 5, the second hand: the quantity crosses, the question does not

**The axis is not this lane's choice.** `docs/KNOWN_ISSUES.md` records the hand
as "11.9 cm ahead of her shoulders", so the quantity is the AHEAD component from
the shoulder midpoint. Of four components on that origin, only world-ahead
reproduces the recorded numbers, to 0.18, 0.00 and 0.01 cm.

    one_hand_snatch_to_other_hand    engine  rendered    gap
    ready f0                          11.92     11.03   0.90
    reach f34                         11.92     11.02   0.90
    contact f48                       12.03     11.05   0.98
    join f70                          20.22     18.08   2.13
    pull_in f97                       12.06     10.51   1.55

**This is the closest agreement in the pack.** Item 5's quantity crosses.

**The question does not, and that belongs in section 1.** It asks about the
TRAVEL, and the travel needs the frame where the hand is furthest out. The engine
puts that at frames 58 and 60 and neither is a phase frame, so no rendered figure
exists at the moment the question is about. The travel stays engine-only: 13.94
and 14.48 cm.

**A CLIP WOULD NOT SETTLE IT, and the running order plans one.** `animation` is
null on every archived receipt, and the animate path records frame counts and
file hashes, never a per-frame joint position. A clip would DRAW the peak and
record nothing about it.

## 7. Two rows of the coach morning were read on the struck pose

Item 7 is STRUCK because `hooks_outside_hand` has two solved poses about 33
degrees apart at the first frame.

On `ac240b2`, which is the agenda's build, the agenda names these:

    the corrected pose                48.22 degrees of turn
    the pose the shipped set reached  15.44 degrees of turn
    item 6, wrist to wrist            45.68 cm
    item 5, the free hand              3.43 out to 14.33, back to 3.48, travel 10.90

On `2413f9d`, this tree and the rendered library:

    the turn, engine                  48.22 degrees
    the turn, rendered figure         45.48 degrees
    item 6, wrist to wrist            40.36 cm
    item 5, the free hand              7.45 out to 21.93, back to 11.28, travel 14.48

**Both bodies now hold the corrected pose**, so only the agenda's figures are
behind.

**SEVEN OF ITEM 6's EIGHT ROWS REPRODUCE EXACTLY, AND THE EIGHTH IS THAT DRILL.**
A single wrong row could be anything. Seven right and one wrong, where the one is
the drill with two solutions, names the mechanism instead of asserting it.

**Item 5's conclusion reverses.** The agenda calls that drill the milder case.
Its `ac240b2` figures are 10.90 cm of travel against the other drill's 14.12.
On `2413f9d` it travels 14.48 against 13.94.
So the two drills agree and it is the WIDER of the two. **That item does not need a
new number, it needs a new question.**

The orchestrator has ordered the amendment and it is the content lane's. This
lane measured and ruled on nothing.

## 8. A flag that is not a finding, and it is the movement lane's

On this build and this five-drill population the ENGINE's own elbow mean is 38.73
cm against the manual's 38.6, a gap of 0.13 cm. Erin's page states that gap at
2.17 cm, from 36.43 on `02b25cd`.

**The number a coach question rests on has moved.** The build differs, the
population differs, and the dial is the movement lane's. This lane claims nothing
else about it.

## 9. The four render rows, for the morning date

Full evidence in `docs/RENDER_ARTEFACTS.md`.

| item | usable in a room | where | build |
|---|---|---|---|
| 17, corrected right hand | **YES** | `.assets/archives/coach-figures-2413f9d/` | `2413f9d` |
| 2, elbow width 31.3, 37.3 | **NO** | nothing at 37.3 exists | none |
| 4, the finger clip | **NO** | 15 clips exist, none usable | none |
| 18, the release angles | **NO** | nothing, and nothing to render yet | none |

**The running order's recommendation to hold the date is CONFIRMED for items 2, 4
and 18, and item 17 comes off the blocking list.** The archive stills do not
depend on Erin's page, so the page hold does not reach them.

**A DEFECT IN THIS LANE'S RECEIPT, UNDER ITEM 2.** No render receipt records the
parameter that produced the picture, in any of the three archives. So
`render_pair(parameter, value_a, value_b)` from
`docs/COACH_REVIEW_SPEC_INTERFACE.md` section 4 cannot be verified even after
somebody renders the pair. **This lane owns it and it is queued.**

## 10. Two defects this lane found in its own instruments

**`docs_number_audit.py` flagged rows it should not have.** `hip` matched inside
"shipped" and `stance` inside "distance", so 76 rows were told not to be
refreshed when they should be. A word boundary alone fixes those and BREAKS
`leftKneeFlexionDegrees` and `double_foot_landing`. The text is now split at each
camel case hump and underscore first: 82 rows unflagged, none newly flagged, and
every one of the 82 named. **That tool had no test at all until now.**

**A load-bearing claim that nothing read.** Three instruments and two papers
asserted that the job files still match the receipts. It was true when each was
written and nothing checked it afterwards. `scripts/archive_agreement.py` now
refuses four ways: a changed job, an absent job, two build stamps in one archive,
and an empty archive.

## 11. What is NOT measured, each with its reason

- **The travel of the second hand on the rendered figure.** The peak is not a
  phase frame and the archive holds no pose there. Every phase frame IS measured.
- **The ball speeds, item 3.** Not a body quantity. No two-body disagreement
  exists for them.
- **The finger closing speed, item 4.** A receipt carries one pose per phase, so
  a rate needs frames the archive does not hold.
- **The release-hand angles.** They wait on the movement lane's flick model.
- **Anything below the hips.** Nothing below the hips is presented as a graded
  value anywhere in this pack.

## 12. Suite state, and what has actually been run

    lane suite, on the MERGED tree    226 tests, OK, 27 skipped
    engine suite                      RUNNING, not yet read

The 27 skips are 17 Blender integration tests and 10 video artefacts absent from
this machine.

**The engine suite line is deliberately not a pass.** An earlier run of it in
this session was piped through `tail`, so the exit code read was the pipe's and
the summary line never reached the file. It is re-running without a pipe and this
line is replaced when the summary is read, not before.

## 13. Instruments, all committed with their numbers

    scripts/archive_agreement.py          refuses unless the tree still solves
                                          what the archived figures show
    scripts/two_bodies_compare.py         the distances, raw and per shoulder span
    scripts/two_bodies_angles.py          elevation, flexion, trunk lean
    scripts/two_bodies_ready_and_join.py  items 6 and 5, and the turn
    scripts/render_artefact_inventory.py  the four render rows
    scripts/docs_number_audit.py          every number's build

Papers: `docs/TWO_BODIES_PAPER.md` and `docs/RENDER_ARTEFACTS.md`.
