# What the key-timed release would cost, measured

The defect is in `docs/RELEASE_SEAM.md`: the flight measures its elapsed time
from the release frame, which is 24 to 65 per cent of a frame later than the
release key. This is the graded cost of correcting it.

**Nothing was changed.** The working tree was clean before this measurement
and clean after it. The patched module is the shipped source text with exactly
one line substituted, executed under another name, so this measures the
shipped path plus the change rather than a re-implementation of it. The
substitution is asserted to appear exactly once before it is applied. No
receipt was written: `solve_movement` was called directly, not `build`.

Measured on `7a3ae92`.

## The control comes first

Two shipped solves of the same drill agree to **0.000000 degrees** on all four
drills. The solve is deterministic here, so a 0.01 degree move below is a real
move and not noise. Without this the small rows would mean nothing.

## The result

**Twenty graded values move. No verdict flips.**

| drill | graded | moved | flipped |
|---|---|---|---|
| `two_hand_snatch_straight_back` | 8 | 6 | 0 |
| `two_hand_catch_chest` | 7 | 5 | 0 |
| `deflect_high` | 8 | 5 | 0 |
| `hooks_jump_pull_in` | 9 | 4 | 0 |

Every move except one is under 0.2 degrees. The exception is the release-phase
elbow on `hooks_jump_pull_in`, which moves 2.19 degrees.

| drill | phase | measure | was | now | move |
|---|---|---|---|---|---|
| `hooks_jump_pull_in` | release | `leftElbowFlexionDegrees` | 49.85 | 47.66 | **-2.19** |
| `hooks_jump_pull_in` | gather | `leftKneeFlexionDegrees` | 66.84 | 67.02 | +0.18 |
| `two_hand_snatch_straight_back` | return | `leftShoulderElevationDegrees` | 78.92 | 79.07 | +0.15 |
| `two_hand_catch_chest` | release | `leftElbowFlexionDegrees` | 41.04 | 40.92 | -0.12 |
| `two_hand_snatch_straight_back` | return | `leftElbowFlexionDegrees` | 41.00 | 40.92 | -0.08 |
| `deflect_high` | ready | `leftKneeFlexionDegrees` | 46.79 | 46.71 | -0.08 |

The size of a move tracks whether a graded phase anchors near the release. The
largest is on the drill whose release key sits furthest into its frame, and it
is graded at the release itself.

## The direction is consistent, and it matters

**All four elbow checkpoints that already fail move FURTHER from their bands.**

| drill | phase | band minimum | gap before | gap after |
|---|---|---|---|---|
| `hooks_jump_pull_in` | release | 50.0 | 0.15 | 2.34 |
| `deflect_high` | send_on | 45.0 | 9.17 | 9.22 |
| `two_hand_snatch_straight_back` | return | 45.0 | 4.00 | 4.08 |
| `two_hand_catch_chest` | release | 55.0 | 13.96 | 14.08 |

The correction puts the ball further along its flight on that frame. The hands
follow the ball, so the arm is straighter, so the flexion falls. The engine
grades a straighter arm as further below a band that asks for a bent one.

This is the third leg of the release conversation, and it points the same way
as the first two. The bands were never shown to be wrong. **The anchor is
late**: these phases are graded at the follow-through rather than at the
moment the ball leaves. A correction that makes the follow-through more
correct makes the reading at that anchor worse, which is what an anchor in the
wrong place does.

## What this does not settle

- **Whether to make the change.** It is a timing defect with a determinate
  answer, but it moves the look of every drill that passes the ball back, so
  it waits for Marius and Erin with the rest of the release question.
- **Whether the release anchor should move first.** If the anchor moves, these
  four gaps are all recomputed against a different frame and this table is
  superseded. The two changes interact and should be decided together, not in
  sequence.
- **The other four drills were not measured.** Only the four that release the
  ball can show this, but `one_hand_snatch_to_other_hand`,
  `two_hand_snatch_pull_in`, `hooks_outside_hand` and `double_foot_landing`
  were not checked for a release at all.
- **Nothing outside the graded set was measured.** The hand orientation rows
  and the snap statistic will move too. Only the coaching checkpoints are
  above.

## Provenance

Measured on `7a3ae92` with a clean tree, before and after. The control, the
one-line substitution and its single-occurrence assertion are what make the
figures comparable; refer to [[p1-comparability-is-per-build]] in kind, since
both sides of every comparison here come from one process and one build.
