# A pose the athlete cannot hold, and the four findings it produced

For two days the engine reported that the hand-mirror fix had straightened the
athlete's stance and brought two populations together. It had done neither.
The solver was absorbing her turn into a joint rotation the body cannot make,
through a degree of freedom the model does not grant.

This document names the mechanism, separates what was real from what was not,
and withdraws the four findings that were not. The withdrawn sentences are
written out rather than replaced, because three of them left this repository.

Measured on `d36af35` with the fix applied. Nothing here is a judgement call.

## The mechanism

A parameter whose own range is ZERO WIDE is locked by the model: the body says
it must be exactly zero. Four such parameters were enabled for the solver —
`l_clavicle_rx`, `r_clavicle_rx`, `l_foot_lean1`, `r_foot_lean1`.

**The limit term is soft.** It pulls a parameter back towards its range; it
does not hold it there. So a locked parameter left enabled sits wherever the
other terms drag it, and the size of the breach is simply the size of the pull.

On `netball_hooks_outside_hand` — the turned drill, whose free arm pulls
hardest — the left clavicle sat **2.34 degrees outside a range of zero, on all
98 of its frames**. Every other drill pulled the same parameter 0.06 to 0.10
degrees and stayed under the quarter-degree reporting tolerance, which is why
it read as one drill's problem rather than as a rule being broken.

The fix removes those four from the enabled set. It removes freedom rather than
adding a constraint, and it touches no weight.

## The three states that settle it

`hooks_outside_hand`'s shoulder line at frame zero, and the mean elbow width at
contact for each population:

| state | shoulder line | both hands | one hand | gap |
|---|---|---|---|---|
| **A** negation, axis free — before the mirror fix | 48.23 | 36.43 | 57.60 | 21.16 |
| **B** mirror, axis free — `ac240b2`, what shipped | **15.44** | 36.40 | **39.49** | **3.09** |
| **C** mirror, axis pinned — this change | 48.22 | 36.43 | 57.39 | 20.96 |

**State C reproduces state A.** The athlete never straightened up and the
populations never converged. B is the artefact.

**The two-handed mean is 36.40 to 36.43 in all three states. It never moved,
which is why nothing caught this.** Every guard, every gate and every review
watched a quantity the artefact did not touch.

## The four findings that fall

Each was published. Each is withdrawn here in the form it was published in.

**1. "The ready stance changed, 48 to 15 degrees."** Published as the headline
of the hand-mirror fix and relayed to Marius and to the rendering lane. It read
that the athlete had been turning her shoulders 48 degrees to compensate for a
hand whose fingers closed wrongly. **She had not.** The turn was being absorbed
into an impossible clavicle rotation. She stands at 48.22 degrees under the pin,
where her track always put her.

**2. "The populations converged, about 20 cm to 3.09."** **They never
converged.** 20.96 cm under the pin.

**3. "The one-handed population is not a population."** This was the headline of
the coach-morning bundle. It argued that two drills 40.95 cm apart, with a
standard deviation of 28.96, could not be averaged, and that the pole question
had therefore been framed wrongly for weeks. **The 19.01 cm reading that made
`hooks_outside_hand` an outlier was the distorted clavicle.** Under the pin the
two one-handed drills read **54.83 and 59.96**: spread 5.13, standard deviation
3.63 — a tighter pair than the two-handed group's 4.09.

The original framing was right all along. The correction was the artefact.

**4. "The library no longer holds a drill turned past 20 degrees while a hand
waits."** Recorded as a library-content gap, put on the coach agenda as a
question about authoring a new drill, and used to justify moving a test's
contract onto a hand-built fixture. **There was no gap.** The drill turns 48.22
degrees. The coach agenda item is STRUCK, not reworded: it asked about content
that already exists.

The synthetic fixture is kept, as belt and braces rather than as the only case.
It costs nothing to hold a contract in two places when one of them is a library
that can change.

## The corrected cost of the hand-mirror fix

Its cost table was measured with the artefact on both sides, so it measured the
artefact. Four states, both hands of each comparison stated:

| comparison | graded values moved | verdicts flipped | largest move |
|---|---|---|---|
| A to B — **what was reported** | 47 | 0 | **23.16** `hooks_outside_hand` contact right elbow, 72.82 to 49.66 |
| D to C — **the hand fix alone**, both sides pinned | 46 | 0 | **3.09** `two_hand_snatch_straight_back` ready left knee |
| B to C — the artefact removed from today's build | 42 | 0 | 22.50 |
| A to D — the artefact removed from the old build | 45 | 0 | 15.72 |

**The 23.16 degree move was the artefact, not the hand fix.** That elbow reads
72.82 before the mirror fix and 72.16 under the pin: it returns to within 0.66
degrees of where it started. The hand fix's real largest graded move is **3.09
degrees, on a knee** — the under-determined channel this engine has moved on
every hand or seed change it has ever had.

No verdict flips in any comparison.

## What stands

The artefact touched posture on one drill. It did not touch these, and each was
verified independently of it.

- **The hand-mirror fix itself.** The right hand is correctly mirrored: both
  hands fan 14.37 cm and every fingertip is the reflection of its opposite. Only
  its apparent postural side-effects were artefacts.
- **The release anchor's three legs.** All four failing checkpoints sit inside
  band where the ball leaves and outside only where they are graded.
- **The ball speed.** One constant, 600 cm/s, with no provenance.
- **The finger ramp.** 89.95 degrees in one frame at the contact frame.
- **The two-handed elbow width**, 36.40 to 36.43 through every state.
- **The dial re-read.** At 31.3 the two-handed mean is 36.43, a gap of 2.17 to
  the manual's 38.6. At 37.3 it is 38.42, a gap of 0.18. That survives.

**The pole question returns to its original two-population form**, and both
populations are now real: 36.43 cm with both hands on the ball, 57.39 with one.

## A prediction this change must satisfy

The rendering lane measured, before it knew about the pin, that between the
pre-fix renders and `ac240b2` six phases improved their athlete-inside-the-ball
figure and **three got worse**: `hooks_outside_hand` contact 7 to 8 vertices
(−0.9 to −1.4 mm), `hooks_outside_hand` gather 1 to 3 (−0.1 to −0.6), and
`deflect_high` contact 9 to 10 (−0.8 to −1.2).

**The two hooks phases should push back on the pinned build.** That drill is the
one the artefact distorted, and the prediction is strong there.

**`deflect_high` is a weaker prediction and is stated as such.** It never
breached the reporting tolerance in any state — worst 0.0614 degrees — and its
contact elbow width moves only 37.15 to 37.23 under the pin. If its intersection
figure does not recover, that is not evidence against the mechanism.

If the two hooks phases do not push back, that is a finding about the pin's
completeness and not about the mechanism, which the three-state table settles
independently.

## Why it took two days

Nothing was careless, and that is the uncomfortable part.

`check_joint_limits.py` reported the breach the whole time. It is a separate
task, so the suite passed 564 tests and the clip gate passed while it exited 1.
**Nothing in the gate read it.** That gap is being closed as its own change.

And the artefact was invisible to every quantity anybody watched. The
two-handed mean never moved. No verdict ever flipped. The clip gate's worst
asserted gap stayed at 0.02 to 0.03 degrees. The only quantities that moved
were on one drill, and each time they moved, the movement was read as a
finding about the athlete rather than as a question about the solver.
