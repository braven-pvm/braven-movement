# Two bodies: what a band set on one costs on the other

Erin grades the engine's skeleton, because that is what the bands measure. She
looks at the MPFB athlete, because that is what the manual prints. They are
different bodies. This measures how far apart they are on the quantities the
coach morning asks her to set.

Measured on build `2413f9d`. **The engine side is solved on this tree and the
rendered side is read from that build's archived receipts.** That is legitimate
for one checked reason: all eleven job files on this tree are byte-identical to
the `jobSha256` each receipt recorded, so the solve here is the solve those
figures were rendered from.

Reproduce with `pixi run --frozen python ../scripts/two_bodies_compare.py`.

## 1. A correction to this lane's own number, before anything else

This lane reported that the elbows read **36.43 cm** on the engine and **32.02
cm** on the rendered athlete, a gap of 4.41 cm, and called it a same-phase
comparison. **It was not.**

- 36.43 cm is a **mean over six drills**, from `docs/COACH_MORNING_2026-09.md`,
  with a spread of 28.90 to 40.37. The spread is wider than the gap that was
  reported.
- It was measured on `02b25cd`, one build older.
- 32.02 cm is **one phase** of one drill on `2413f9d`.

A mean against a single phase, across two builds. That is the population fault
this lane has caught three times in other people's work this week.

**The matched figures are below and the gap is 5.66 cm, not 4.41.** The finding
survives the correction. The number did not.

## 2. The elbows, matched as closely as this lane can match them

Five drills whose both-hands phase is named `contact`, on `2413f9d`:
`deflect_high`, `hooks_jump_pull_in`, `two_hand_catch_chest`,
`two_hand_snatch_pull_in`, `two_hand_snatch_straight_back`.

    engine elbows      mean 38.73 cm    37.52 to 40.47
    rendered elbows    mean 33.07 cm    32.02 to 34.46
    the means differ         5.66 cm

**This is NOT the page's six-drill population.** The page's six were chosen on
an older drill set, before `bounce_pass` and `one_hand_high_pass` existed, and
the two one-handed drills it excluded are named in its own withdrawn section.
This lane cannot reconstruct that six and does not claim to have.

## 3. Most of the raw gap is two different-sized people, and that is not a defect

At every phase measured, the engine's shoulders are wider than this rig's. A
distance on one body is simply not the same distance on the other.

    shoulders   raw gap  +4.76 to +11.79 cm, median +10.00
    elbows      raw gap  +3.93 to +16.31 cm, median +10.91
    wrists      raw gap  +0.34 to +11.71 cm, median  +0.50

So a raw gap is the wrong instrument. The comparable quantity is each distance
as a fraction of that body's OWN shoulder span.

**The shoulders row is 0.000 by construction**, because the shoulder span is the
divisor. It is reported so the table is complete, and it is not evidence of
agreement.

## 4. The finding: the band does not transfer, in either form

At contact, over the five drills, as a fraction of each body's own shoulder span:

    engine elbows      1.022 shoulder spans
    rendered elbows    1.130 shoulder spans
    difference        -0.109

**The rendered athlete's elbows are absolutely NARROWER by 5.66 cm and
relatively WIDER by 0.109 shoulder spans.** Both statements are true at once,
because her shoulders are narrow while her arms are aimed by a direction and a
fraction of an arm, which do not shrink with the shoulders.

Across all phases the ratio difference runs −0.213 to +0.242 for the elbows and
−0.178 to +0.126 for the wrists. It is not a constant.

**So no restatement of the band makes it transfer.** In centimetres it is wrong
by 5.66. As a fraction of shoulder span it is wrong by 0.109 at contact and by a
varying amount elsewhere. A band she sets on the skeleton is not a band that
describes the figure a coach sees.

## 5. How much of it the open girdle narrowing explains

The girdle narrowing is recorded per phase in the same receipts, as
`wantedWidthMm` minus `renderedWidthMm`. At `two_hand_catch_chest/contact` it is
39.36 mm, against a 56.6 mm elbow difference at that phase.

**Same direction, same order, and this lane does not attribute the remainder.**
The two bodies have different arm lengths, and an arm length difference is a body
fact rather than a defect. Naming a cause for the rest would be a claim about a
mechanism nobody has measured.

## 6. A flag, not a finding: the premise may be stale

On this build and this five-drill population, the ENGINE's own elbow mean is
**38.73 cm** against the manual's **38.6**, a gap of 0.13 cm. The page states
the gap at 31.3 is **2.17 cm**, from 36.43 on `02b25cd` over six drills.

**This lane does not claim the dial question is answered.** The build differs,
the population differs, and the dial is the movement lane's. What this lane can
say is that the number the question rests on has moved, and that whoever owns
the dial should re-measure it on `2413f9d` before Erin is asked to close a gap
that may no longer be the size the question describes.

## 7. What is not measured here

- The other quantities the morning sets. The shoulder elevation floor, the ball
  speeds and the release-hand angles are not in this table. Elbow width was
  taken first because item 2 is the one she is asked.
- Anything below the hips. The landing item is excluded, because nothing below
  the hips may be presented as a graded value on this rig.
- Whether the engine's six-drill population and this five-drill one would give
  the same answer. They cannot be compared without the older drill set.
