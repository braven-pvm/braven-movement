# The contact hitches are a sub-frame timing defect at the release

All four hitches the snap instrument reports are one mechanism. It is found,
it is proven to the last decimal, and **nothing here is fixed**. The change it
implies is described at the end and waits for a ruling.

Measured on `9cf25a4`, the tip that passed gate 2b. **No solve was needed.**
The carried ball's position comes from the motion track and the rest pose, not
from the solved joint angles, so every number below is reproducible without
the solver.

## What the instrument sees

`snap_report` reports a stall on four drills. The ball moves a normal amount,
then almost nothing, then a full frame of flight.

| drill | frame | before | at the release | after |
|---|---|---|---|---|
| `two_hand_snatch_straight_back` | 88 | 0.75 | **0.21** | 10.13 |
| `two_hand_catch_chest` | 90 | 1.59 | **0.36** | 10.14 |
| `deflect_high` | 70 | 1.64 | **0.95** | 10.14 |
| `hooks_jump_pull_in` | 102 | 1.53 | **0.91** | 10.21 |

Centimetres per frame.

## What it is not

The carried ball is an offset placed in a per-frame frame, so a chest moving
against the carry would produce exactly this. **It does not.** Splitting each
step into the carry offset's own change and the frame's motion:

| drill | chest contribution |
|---|---|
| `two_hand_snatch_straight_back` | 0.0000 cm |
| `two_hand_catch_chest` | 0.0000 cm |
| `deflect_high` | 0.0000 cm |
| `hooks_jump_pull_in` | 0.33 cm, about 20 per cent |

The athlete is still during the carry on three of the four. Only the hooks
drill contributes anything, and it is the drill that turns. **The chest is not
the mechanism.** This was the leading hypothesis and the measurement refutes
it.

## What it is

**The declared release phase never lands on a frame.**

The last carry key is authored at exactly the declared release phase. The
release frame is the first frame at or past that phase, so it is always late,
by a fraction of a frame that nobody chose.

| drill | release phase | that is frame | release frame | dropped |
|---|---|---|---|---|
| `two_hand_snatch_straight_back` | 0.90 | 87.30 | 88 | 70 per cent |
| `two_hand_catch_chest` | 0.92 | 89.24 | 90 | 76 per cent |
| `deflect_high` | 0.80 | 69.60 | 70 | 40 per cent |
| `hooks_jump_pull_in` | 0.95 | 101.65 | 102 | 35 per cent |

Two things then happen on that one frame, and both drop motion:

1. **The carry stops at the key.** Past its last key the sampler holds the
   final offset, so the carry contributes only the part of the frame that
   falls before the key.
2. **The flight has not started.** The ballistic launch measures its elapsed
   time from the release FRAME, so that time is zero and the flight
   contributes nothing at all.

The ball therefore travels the fraction of a carry step that fits before the
key, and nothing else, on the frame where it is supposed to be thrown.

**The arithmetic is exact.** Predicting the release-frame step as the carry
truncated at the key reproduces the measurement on all four drills:

| drill | measured | predicted | agreement |
|---|---|---|---|
| `two_hand_snatch_straight_back` | 0.2123 | 0.2123 | 0.000000 cm |
| `two_hand_catch_chest` | 0.3563 | 0.3563 | 0.000000 cm |
| `deflect_high` | 0.9520 | 0.9520 | 0.000000 cm |
| `hooks_jump_pull_in` | 0.9113 | 0.9113 | 0.000000 cm |

## The change this implies

Time the flight from the release key, not from the release frame. The ball is
already airborne for 5.8 to 12.7 milliseconds when that frame is drawn, and
the code currently says it is not.

The launch point does not move. Past the key the sampler clamps, so the
release frame already sits on the key, and the same clamp that causes the
stall makes the origin correct for the correction.

Measured, not estimated:

| drill | sequence now | sequence corrected |
|---|---|---|
| `two_hand_snatch_straight_back` | 0.75, **0.21**, 10.13 | 0.75, 7.30, 10.10 |
| `two_hand_catch_chest` | 1.59, **0.36**, 10.14 | 1.59, 8.06, 10.11 |
| `deflect_high` | 1.64, **0.95**, 10.14 | 1.64, 3.61, 10.12 |
| `hooks_jump_pull_in` | 1.53, **0.91**, 10.21 | 1.53, 4.43, 10.19 |

The stall becomes a ramp on all four, and the frame after the release moves by
less than 0.04 cm, so the flight itself is undisturbed.

## What is not settled

- **This is a timing defect and not a matter of taste.** The ball leaves the
  hand when the technique says it does. There is no coaching judgement in
  that. What does want a coach's eye is the resulting look, in the same way
  the hand mirror does.
- **The graded values are not measured here.** The hands follow the ball, so
  release-phase checkpoints will move. That is a solve, and it must be
  measured before the change is proposed rather than after.
- **`hooks_jump_pull_in` carries a second, smaller term**, the 0.33 cm of
  chest motion above. It is 20 per cent of that drill's step and it is NOT
  explained here. It does not affect the mechanism, which reproduces exactly
  on all four.
- **Whether any other seam has the same shape.** The contact seam was not
  examined. The release key is authored on a round phase, and so are other
  keys, so the same fraction-of-a-frame loss can occur anywhere a regime ends
  on an authored phase.

## Provenance

Read from the working tree at `9cf25a4`, the tip that passed gate 2b. The
tables come from two probes over the four drills. The chest split inverts the
frame placement rather than reading an internal, so it measures the shipped
path rather than a copy of it.
