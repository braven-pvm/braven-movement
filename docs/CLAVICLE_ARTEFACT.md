# Two solver basins, and the four findings that came from reading one

For two days the engine reported that the hand-mirror fix had straightened the
athlete's stance and brought two groups of drills together. It had done
neither. `netball_hooks_outside_hand` has **two solved poses about 33 degrees
apart in ready-stance turn**, and which one the solver reaches depends on the
composition of the enabled parameter set.

This document names that, separates what was real from what was not, and
withdraws the four findings that were not. The withdrawn sentences are written
out rather than replaced, because three of them left this repository.

**The filename is historical.** A first version of this document blamed a
clavicle rotation. That explanation was refuted by a control described below,
and the file keeps its name only so existing links still resolve.

Measured on `d36af35` with the fix applied.

## What was actually wrong, and what only looked wrong

Four parameters have a limit range of ZERO WIDTH — the model says they must be
exactly zero — and all four were enabled for the solver: `l_clavicle_rx`,
`r_clavicle_rx`, `l_foot_lean1`, `r_foot_lean1`. **Handing the solver a
parameter the model has locked is wrong on the model's own word**, and that is
the whole justification for excluding them. It is not justified by load: on
`d36af35` `foot_lean1` peaks at 0.0003 degrees and is inert.

On `netball_hooks_outside_hand` the left clavicle sat 2.34 degrees outside a
range of zero on all 98 of its frames. That is a real breach and the fix
removes it.

**It is not what produced the stance change, and the first version of this
document said it was.**

## The control that refuted it

Excluding an UNRELATED axis — `head_twist`, which has a real range and is not
locked at all — undoes the stance change exactly as pinning the clavicle does:
turn 48.22, elbow width 54.85. So does excluding either foot alone. **In every
one of those solves the still-enabled `l_clavicle_rx` sits at 0.0000 degrees.**

A magnitude check settles it without any of that: **a 2.34 degree rotation
cannot hold a 33 degree shoulder-line turn.** I did not run it.

What actually differs in the artefact state is elsewhere in the body.
`spine_twist0` at frame zero reads −11.56 degrees there, against +51.57 —
saturated at its own limit — in every other state, and the root rotation is
wound to 1030, 769 and 683 degrees.

**The state is a distinct local minimum, reached only with that exact
54-parameter set.** The breach is what the instrument CAUGHT in that basin, not
what created it. Changing the set's composition at all moves the solver to the
other basin.

**That fragility is the finding.** One drill has two solved poses 33 degrees
apart, and the choice between them is decided by which parameters happen to be
enabled.

## The three states

`hooks_outside_hand`'s shoulder line at frame zero, and the mean elbow width at
contact for each group:

| state | shoulder line | both hands | one hand |
|---|---|---|---|
| **A** negation, locked free — before the mirror fix | 48.23 | 36.43 | 57.60 |
| **B** mirror, locked free — `ac240b2`, what shipped | **15.44** | 36.40 | **39.49** |
| **C** mirror, locked pinned — this change | 48.22 | 36.43 | 57.39 |

**State C reproduces state A.** B is the outlier, and B is one basin.

**The two-handed mean is 36.40 to 36.43 in all three states. It never moved,
which is why nothing caught this.** Every guard, gate and review watched a
quantity the basin change did not touch.

## The four findings that fall

Each was published. Each is withdrawn here in the form it was published.

**1. "The ready stance changed, 48 to 15 degrees."** The hand-mirror fix's
headline, relayed to Marius and to the rendering lane. She never straightened
up. The solver reached a different basin.

**2. "The populations converged, about 20 cm to 3.09."** They never converged.

**3. "The one-handed population is not a population."** The coach-morning
bundle's headline. It argued that two drills 40.95 cm apart could not be
averaged. The 19.01 cm reading came from the other basin.

**4. "The library no longer holds a drill turned past 20 degrees while a hand
waits."** Recorded as a library-content gap and put on the coach agenda. There
was no gap. The drill turns 48.22 degrees. The agenda item is STRUCK.

## What the numbers support, and what they do not

Under the fix the two one-handed drills read 54.83 and 59.96 cm.

**Neither "a population" nor "not a population" is a claim two points can
carry**, and this document made the second of those errors after the coach
bundle made the first. The defensible statement is the measurement:

> Two one-handed drills sit 5.13 cm apart, at 54.83 and 59.96 cm. Each is 18.4
> to 23.5 cm above the two-handed mean of 36.43, and 14.5 to 19.6 cm above that
> group's widest member at 40.37.

A standard deviation over two points is the range divided by the square root of
two. Comparing it to a six-point group's spread is illegitimate in either
direction, and the coach bundle's 28.96 was the same error pointing the other
way.

## The corrected cost of the hand-mirror fix

Its cost table was measured with the basin change on both sides. A fourth
state — negation WITH the locked parameters pinned — isolates the hand fix:

| comparison | moved | flips | largest |
|---|---|---|---|
| A to B — **what was reported** | 47 | 0 | **23.16** |
| D to C — **the hand fix alone**, both sides pinned | 46 | 0 | 3.09 |
| B to C | 42 | 0 | 22.50 |
| A to D | 45 | 0 | 15.72 |

**The 23.16 degree move belongs to the basin change, not to the hand fix.** That
elbow reads 72.82 before the mirror fix and 72.16 under the pin.

**The 3.09 is a bistable knee and should not be quoted as the hand fix's cost
either.** `two_hand_snatch_straight_back` ready left knee reads 52.60 in states
A and C and 55.69 in B, D and E; it flips under any perturbation, including one
with no hand change in it. **Seven of the largest eight moves are knees**; the
eighth is the 0.17 degree elbow below.

**The hand fix's largest move away from the knee channel is 0.17 degrees**, on
`two_hand_snatch_straight_back` return left elbow. That is the honest figure.

The largest change to any grip figure is **0.20 cm**, on `hooks_outside_hand`'s
worst palm-skin gap, 0.013 to 0.214 cm. Every other drill changes by 0.009 cm
or less.

An earlier version glossed that as moving the drill "from unusually tight into
the library's ordinary range". **That gloss is dropped**, because 0.013 was not
unusual: `one_hand_snatch_to_other_hand` reads 0.021 and `double_foot_landing`
0.024 on the same build. The numbers are the statement.

## Excluding only what was proved

A sixth state, E, excludes the clavicle pair alone and leaves the feet enabled.
**Posture is identical to C.** 41 graded values differ, all by 3.25 degrees or
less, and all in the knee channel.

So the feet are inert and their exclusion is not supported by any measurement.
It is supported by the model, which says their range is zero. That is a
sufficient reason and it is the only one claimed here.

## What stands

- **The hand-mirror fix itself.** Both hands fan 14.37 cm and every fingertip is
  the reflection of its opposite.
- **The release anchor's three legs.**
- **The ball speed.** One constant, 600 cm/s, with no provenance.
- **The finger ramp.** 89.95 degrees in one frame at the contact frame.
- **The two-handed elbow width**, 36.40 to 36.43 through every state.
- **The dial re-read**, whole row on the pinned build. At 31.3 the two-handed
  mean is 36.43, narrowest 28.90, widest 40.37, a gap of 2.17 to the manual's
  38.6. At 37.3 it is 38.42, narrowest 30.57, widest 42.37, a gap of 0.18.

**The pole question returns to its original form**, with the one-handed drills
described by the measurement above rather than by the word "population".

## A prediction this change must satisfy

The rendering lane measured, before it knew about the pin, that three phases
got worse between the pre-fix renders and `ac240b2`: `hooks_outside_hand`
contact 7 to 8 vertices, `hooks_outside_hand` gather 1 to 3, and `deflect_high`
contact 9 to 10.

**The two hooks phases should push back.** That drill is the one that changed
basin.

**`deflect_high` is a weak prediction and is stated as such.** It never breached
the tolerance in any state, worst 0.0614 degrees, and its contact elbow width
moves only 37.15 to 37.23. If it does not recover, that is not evidence about
the basin.

## How long this was wrong, precisely

Two breaches are easy to conflate and they have different ages.

- **The 0.499 degree breach on `l_clavicle_rz`** — a real axis with a real range
  — was present at `716b3eb`, along with one frame of `two_hand_catch_chest` at
  0.251 degrees on `r_thumb2_rz`.
- **The 2.34 degree breach on `l_clavicle_rx`**, the locked axis, dates from
  `ac240b2` at 14:04 on 1 September. **One day, not weeks.**

`check_joint_limits.py` reported it for that day and exited 1 while the suite
passed 564 tests and the clip gate passed, because nothing in the gate read it.
That is now a suite row.

## Why the wrong explanation survived a day

The clavicle breach and the stance change appeared together, on the same drill,
in the same build. A mechanism that joins them is easy to write and it fit
every number I had. What it did not survive was a control I did not run:
changing the enabled set some other way.

The magnitude check was available the whole time and cost nothing. **2.34
degrees cannot account for 33.** Writing that sentence down would have stopped
the explanation before it was published.
