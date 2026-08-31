# The right hand is not the mirror of the left, and the evidence for changing it

Every number here was taken on `378fea0` with a clean tree. Nothing in this
document changes any code. The change it describes moves the look of every
drill, so it waits for Marius alongside the elbow pole angle.

## What the code does

`finger_wrap.spread_fingers` opens the hand once, as a posture the whole drill
carries. It negates every value on the right:

    opened[names.index(name)] = value if side == "l" else -value

and says why in a comment: "The left and right hands fan in opposite
directions." That is a claim about the rig, and the rig disagrees.

## 1. The rig's own convention, read from the rig

The rest pose is symmetric about `x = 0` to within 0.00005 cm, so a mirror is
the reflection that negates x. That is measured, not assumed.

Setting the same parameter on both hands and comparing the left finger's ray
against the right's, reflected:

| parameter | same sign | negated |
|---|---|---|
| `index1_ry` | 0.01 | 80.21 |
| `middle1_ry` | 0.00 | 20.63 |
| `ring1_ry` | 0.00 | 25.21 |
| `pinky1_ry` | 0.01 | 80.21 |
| `thumb1_ry` | 0.02 | 13.71 |

Degrees between the two rays. **The same sign mirrors. The negation is what
breaks it.** The rig already handles the mirroring, and negating the parameter
un-mirrors it.

## 2. What the posture actually is

| | left fan | right fan |
|---|---|---|
| as shipped | 14.37 cm | **1.75 cm** |
| same sign on both | 14.37 cm | 14.37 cm |

The fan is index tip to pinky tip. A right hand opened to 1.75 cm is not
opened. Reading the four tips across the hand, index to pinky:

    as shipped   -42.99  -43.65  -43.27  -42.78    the fingers have crossed
    same sign    -50.63  -46.11  -40.41  -36.26    exactly the left's sequence

A rising sequence is index, middle, ring, pinky in anatomical order. The
shipped right hand is not in order.

## 3. The control: the arm mirrors and the hand does not

At contact on a square two-handed drill, the two arms should be mirror images.
Degrees between each left segment and its right counterpart, reflected:

| drill | upper arm | forearm | index | pinky | thumb |
|---|---|---|---|---|---|
| `two_hand_catch_chest` | 0.07 | 0.07 | 86.85 | 79.88 | **108.77** |
| `two_hand_snatch_pull_in` | 0.03 | 0.00 | 88.84 | 80.90 | **106.64** |

**The solver found a symmetric arm to within a tenth of a degree, and the hand
parameters break it by 80 to 109.** This is the strongest of the five, because
it needs no reference pose and no assumption about what the hand should do: it
compares the athlete against herself.

## 4. The thumb, from the instrument rather than a script

`handOrientation` rows on `378fea0`, holding phases only, `thumbUpDegrees`
against world up. Zero is a thumb pointing straight up.

| drill | phase | left | right | gap |
|---|---|---|---|---|
| `two_hand_snatch_straight_back` | control | 67.8 | 45.9 | 21.9 |
| `two_hand_catch_chest` | contact | 68.4 | 46.7 | 21.7 |
| `two_hand_snatch_pull_in` | contact | 67.2 | 46.0 | 21.2 |
| `one_hand_snatch_to_other_hand` | contact | 64.3 | 45.7 | 18.6 |
| `hooks_outside_hand` | contact | 64.1 | 46.6 | 17.5 |
| `deflect_high` | contact | 61.5 | 47.9 | 13.6 |
| `two_hand_catch_chest` | pull_in | 56.1 | 62.9 | **−6.8** |

Eighteen holding phases, median gap 14.4 degrees, worst 21.9. A mirrored pair
reads zero. **The right thumb is the one closer to straight up**, everywhere
except the pull-in phases, where the sign reverses. That reversal is recorded
rather than explained; nobody has looked into it.

**Erin Burger's note on the chest catch reads "Thumbs shouldn't be up."** The
right thumb at that drill's contact is 21.7 degrees closer to straight up than
the left. This is a candidate mechanical root for her note. It is not proof:
she marked a pose, not a thumb angle, and no coach has read these numbers.

## 5. What the change would cost, measured then reverted

| | |
|---|---|
| graded values moved | 41 |
| **verdicts flipped** | **0** |
| largest graded move | `deflect_high` ready left knee, 41.75 to 51.01 |
| `handOrientation` rows moved | 95 |

The largest graded move is a knee, which is the under-determined channel this
solver has moved on every hand or seed change so far.

The instrument's own breakdown is the fifth piece of evidence, and it is the
one that says the fix touches only what it should:

| measure | rows | median | worst |
|---|---|---|---|
| `rightThumbUpDegrees` | 33 | 21.7 | 33.4 |
| `rightThumbToBallDegrees` | 33 | 2.7 | 21.6 |
| `rightFingerUpDegrees` | 14 | 0.1 | 0.2 |
| `leftThumbUpDegrees` | 9 | 0.1 | 0.2 |
| `leftThumbToBallDegrees` | 6 | 0.1 | 0.1 |

**The right hand moves and the left does not.** A right-hand-only defect,
corrected, should look exactly like this.

## What is not settled

- **No coach has read any of it.** The instrument is report-only and has no
  bands. Whether the corrected hand is what the manual's photographs show is a
  coaching judgement, and it is the reason this waits.
- **The pull-in sign reversal**, above. Measured, unexplained.
- **The transition question**, which is separate and older: the fingers change
  by up to 90 degrees in one frame at contact, and now also at release. Whether
  that reads acceptably at 60 fps wants a person watching a render, and if it
  does not, the answer is probably a ramp on the curl rather than a change to
  any rule here.

## Provenance

Every figure above comes from `378fea0` with a clean tree. Pieces 1 and 2 are
rest-pose geometry and need no solve. Pieces 3, 4 and 5 come from the solved
library and its receipts, whose `generatedFrom` records that commit.

An earlier version of piece 4 quoted the left thumb at contact on the two
one-handed drills as 77.5 and 77.6 degrees. Those were wrong: they were read
while the free hand was still fisted, before `378fea0` fixed it. They now read
64.1 and 64.3. The two-handed rows were never affected and are unchanged.
