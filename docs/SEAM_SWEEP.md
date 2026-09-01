# Every regime boundary in the library, checked for the same defect

`docs/RELEASE_SEAM.md` found a sub-frame loss where the athlete lets go. This
asks every other boundary in every drill whether it has the same shape.

**The answer is no. Contact is clean on all eight drills, and so is the
incoming pass. Only the athlete's release is affected.**

No solve. Measured on `7a3ae92`. Eight drills carry both a ball and a
technique; four of them release the ball.

## The three boundaries

| boundary | what changes | drills |
|---|---|---|
| the passer lets go | stationary in his hand, then flying | 8 |
| contact | flying, then carried | 8 |
| the athlete lets go | carried, then flying | 4 |

## How each one was tested

Each boundary gets a prediction, and the prediction is what makes the test
mean something. A boundary that merely "looks smooth" proves nothing.

- **The passer**: if the flight is sampled correctly, the first frame after
  the key moves by the share of a frame that FOLLOWS the key.
- **Contact**: if the carry starts where the flight ended, the step across
  contact equals the step before it.
- **The athlete**: if the flight has not started, the frame moves by the carry
  share alone, and the flight contributes nothing.

Every prediction holds, on every drill, within **0.8 per cent of a flight
frame**. The worst row is 0.8 per cent and most are under 0.3.

## Contact is clean, and this answers the calibration question

| drill | step before contact | step at contact | difference |
|---|---|---|---|
| `deflect_high` | 10.0196 | 10.0778 | 0.6% |
| `double_foot_landing` | 10.0316 | 10.0033 | 0.3% |
| `hooks_jump_pull_in` | 10.0142 | 9.9953 | 0.2% |
| `hooks_outside_hand` | 10.0074 | 10.0205 | 0.1% |
| `one_hand_snatch_to_other_hand` | 10.0285 | 10.0818 | 0.5% |
| `two_hand_catch_chest` | 10.0207 | 10.0717 | 0.5% |
| `two_hand_snatch_pull_in` | 10.0718 | 10.1120 | 0.4% |
| `two_hand_snatch_straight_back` | 10.0276 | 10.0787 | 0.5% |

Centimetres per frame. The ball crosses into her hands without a step.

The reason is structural rather than lucky. **Contact is chosen by a distance
test on frames, so there is no authored phase to fall between two frames**, and
the carry's first key is the flight's own position at that frame. The code
says so where it is built: the author writes where the ball goes, never where
it starts.

**Nothing calibrated at contact is affected by the release defect.** The arm
constants are measured at contact, and contact is clean.

## The incoming pass is clean, and WHY is the useful part

The passer's release phase also fails to land on a frame, by 11 to 85 per cent
of one. It loses nothing.

| drill | key lands on | first flying frame | share after the key | measured | predicted |
|---|---|---|---|---|---|
| `two_hand_snatch_straight_back` | 31.85 | 32 | 14.5% | 1.4985 | 1.5028 |
| `double_foot_landing` | 58.77 | 59 | 22.7% | 2.3389 | 2.3446 |
| `hooks_jump_pull_in` | 43.73 | 44 | 26.9% | 2.9351 | 2.9482 |
| `two_hand_snatch_pull_in` | 36.69 | 37 | 31.5% | 3.2753 | 3.2854 |
| `one_hand_snatch_to_other_hand` | 31.56 | 32 | 43.6% | 4.4930 | 4.5036 |
| `hooks_outside_hand` | 32.40 | 33 | 60.2% | 6.1914 | 6.2036 |
| `deflect_high` | 20.24 | 21 | 76.4% | 7.9663 | 7.9888 |
| `two_hand_catch_chest` | 27.11 | 28 | 88.8% | 9.1685 | 9.1797 |

The ball moves by exactly the share of the frame it has been flying for.

**The incoming flight is a function of phase.** It is asked where the ball is
at this phase, and it answers correctly whatever the frame grid does.

## The principle, and it names the defect precisely

**A regime sampled as a function of phase is immune. A regime integrated
forward from a frame index is not.**

The incoming flight is sampled by phase. The outgoing flight is integrated
from the release frame, with its elapsed time measured from that frame rather
than from the key.

They are the same physical event, in the same file, handled two ways, and only
one of them is right. That is what makes this a defect rather than a
limitation: the correct pattern is already present a few lines away.

## What is not settled

- **The fix is not made and not proposed here.** Its graded cost is in
  `docs/RELEASE_TIMING_COST.md`, and the change waits with the rest of the
  release question.
- **Boundaries inside a regime were not tested.** Interior carry keys are
  interpolated through, not clamped at, so the mechanism cannot apply. That is
  a reading of the sampler, not a measurement.
- **`two_hand_snatch_pull_in`, `one_hand_snatch_to_other_hand`,
  `hooks_outside_hand` and `double_foot_landing` never release the ball**, so
  they have two boundaries rather than three. They are not evidence that a
  release is clean; they have none.

## Provenance

Measured on `7a3ae92` with a clean tree. The ball's world path comes from the
motion track and the rest pose, so no solve was involved. An earlier run of
this sweep reported the passer's dropped share inverted, at 88.8 per cent
where the true figure is 11.2. It was caught by predicting the step rather
than eyeballing the column, which is the reason each boundary carries a
prediction above.
