# The shoulder field sends a position for a joint that has none

A decision paper for Marius, prepared by the movement lane on 2026-09-07 and
**rebuilt on the same day after an independent review refuted its argument.**
It proposes no change and none has been made; `shoulderShiftFromRestInTorsos`
is unchanged on `main`.

**What the review left standing and what it removed** is set out in the last
section, because a paper that quietly replaces its own reasoning is worth less
than one that shows where it was wrong.

## The central number, which the first draft never stated

**The two rigs' rest clavicles point 32.72 degrees apart.** The chord depends
on WHICH bone it is swept on and so is given with its bone: **7.12 cm at the
rig's clavicle, 9.94 cm at the engine's**. An earlier draft wrote "a chord of
7.11 cm" with no bone named, which is a length without its inputs in the row
that exists to insist on them. Computed by the review from the rendering lane's
own committed
landmark table (`scripts/landmark_comparison.py`, re-measured in
`REVIEW-rendering-0b2495c.md`) against this engine's rest pose. It is not a
fresh measurement of that rig, and the table it rests on is.

That is a **larger** rest difference than the ~2.5 cm fore-and-aft posture gap
already recorded against this field, and it was recorded nowhere. It is the
quantity every option below has to answer, and the first draft of this paper
argued about divisors without ever naming it.

## What each side measures

**The consumer.** `scripts/clavicle_divisor_probe.py`, with the review's
independent rebuild agreeing to 0.018 mm:

| quantity | value |
|---|---|
| shoulder targets the job transmits | **102** (51 graded phases, both sides) |
| how many lie on the rig's clavicle sphere | **none** |
| worst residual, the ruled TORSO divisor | **52.09 mm** |
| worst residual, a CLAVICLE divisor | **31.03 mm** |

The probe reads 52.09 and 31.03; the review's independent rebuild reads 52.11
and 31.05 on the same targets, agreeing to 0.0181 mm on all 96 receipts. Both
pairs appear below where each instrument is quoted, and **the 0.02 mm between
them is four-decimal landmark rounding**, not a disagreement.
| the two clavicle-to-torso ratios | 0.35553 against 0.29530 |

**The sender.** `scripts/engine_clavicle.py`, and the pivot figure is **per
drill**, because the library maximum belongs to one drill alone:

| drill | sternal-end travel |
|---|---|
| `hooks_outside_hand` | **6.25 cm** |
| `one_hand_high_pass` | 2.14 |
| every other drill | 1.66 to 1.98 |

The median over the 102 targets is **1.46 cm** and the 90th percentile 1.97;
only four targets exceed 2.5 cm and all four are on `hooks_outside_hand`.

## What the divisors do, stated correctly

A clavicle rotates about its sternal end and does not stretch, so a shoulder's
reachable positions form a **sphere surface** — two degrees of freedom — while
the field transmits a **three-vector position**.

**A divisor scales the shift from the REST SHOULDER**, not along the line from
the pivot; the first draft said the latter and it was wrong.

**AND THE DECOMPOSITION THE FIRST DRAFT OFFERED IS WITHDRAWN.** It read the
52.09 → 31.03 as "21.06 mm of length and 31.03 mm of orientation". The review
refuted it by measurement: at that same worst target, the clavicle-divisor
residual **with the sternal end's travel removed is 54.72 mm**, larger than the
31.05 it was supposed to decompose. The two numbers do not add, the split was
arithmetic dressed as a mechanism, and nothing replaces it except the 32.72
degrees above.

## The options

### A. Transmit a clavicle rotation from rest

**It is TWO fields, not one.** The first draft said the pivot displacement is
"carried by the existing machinery". No field carries it, and the consumer's
`rotate_bone_toward` cannot move a bone head. Without a transmitted sternal-end
position the ball anchor inherits the pivot travel — **1.46 cm median, 6.25 cm
worst** — against today's worst anchor error of 20.45 mm.

**And the knuckle precedent argues against it.** The first draft cited
`knuckleLimitsDegrees` as settling the axis convention "the same way". Read as
the handoff has it, at `HANDOFF_RENDERING.md:148-152`, it says the opposite: a
**POSE** crosses this boundary as **geometry**, because a rotation only means
something against the rest pose it was measured in and the two rigs do not
share one; a **RANGE OF MOTION** crosses as a rotation about the anatomical
axis. (That is a faithful truncation of the rule, not a quotation; read it
there.) `knuckleLimitsDegrees`
is a range of motion. This field is a pose.

So a rotation from rest would carry the **32.72 degrees in every frame**, which
is the difference it was supposed to remove.

### B. Normalise by clavicle length

Worst residual 52.09 → 31.03 mm, and still none of the 102 on the sphere. A
scalar changes the shift's length, not its direction, and the rest directions
differ by 32.72 degrees. It buys 40 per cent of the error and keeps the shape
that caused it.

### C. The consumer projects onto its own sphere

**This is the status quo written down, not a new act**: the consumer already
lands on the radial projection. Its value would be that the contract says so
and bounds it. Its cost is that the projection moves each target by up to
52.09 mm in a direction the engine never chose.

### D. Transmit a clavicle DIRECTION, plus the sternal end's position

**The option the precedent actually points at**, and absent from the first
draft. `arms.direction` is a unit vector, shoulder to wrist, and it is how this
job already crosses a pose. A direction needs **no axis convention** and no
shared rest pose: the consumer places its own bone, of its own length, along
the transmitted direction.

- **The 102 targets** land on the consumer's sphere by construction, because a
  direction plus its own radius **is** a point on its own sphere.
- **The girdle width** becomes the consumer's own clavicle length at the
  transmitted direction.
- **It is two fields as well** — a direction and the sternal end's position —
  and the second is the same field option A needs, so the pivot travel is
  answered for both or for neither.
- **IT HAS A COST AT REST, AND IT IS THE SAME 32.72 DEGREES.** A WORLD
  direction is not measured from anybody's rest pose, so nothing is carried
  across from this rig's — but the consumer must then turn its own rest
  clavicle **32.72 degrees to meet it, in every frame including a standing
  one**. `zero at rest` is lost: the field would put `clavicleTurnedDegrees` at
  32.72 with the athlete standing still. An earlier draft said "the 32.72 does
  not travel with it", which is true of the arithmetic and misleading about the
  pose.

## The turned drill, which dominates every worst number

`hooks_outside_hand/facing_away` right, frame 0, is the worst target for the
residual, the pivot travel and the rotation. **It is the library's only turned
drill**: `trunkTurnDegrees` reads 48.0 there and **0.0 on every other drill**.

The rotation from rest, per drill, in the world and in the review's trunk frame
(origin `root`, up `root`→`c_neck`, across from the hip line):

| | world | trunk frame |
|---|---|---|
| `hooks_outside_hand` | 3.5 to **65.5** | 2.4 to 34.9 |
| every other drill | 1.2 to 24.7 | 1.1 to 37.0 |

**The 65.5 is a world-frame angle containing the turn.** At that one target it
reads **12.2 degrees** in the trunk frame, which this lane reproduced exactly
from the review's definition.

**THE TRUNK COLUMN IS NOT WHAT AN EARLIER DRAFT SAID IT WAS, and the reason is
a finding of its own.** That draft explained the other drills' higher maxima as
the trunk's LEAN. It is not the lean: the frame is pinned to the HIP LINE, and
**the solver yaws the pelvis on every drill, including the square ones** — 10.5
to 24.5 degrees, and `chest_pass` sits at 15.7 on all 96 frames with its feet
symmetric to 0.002 cm and its shoulders to 0.01. The column is therefore the
world angle **plus or minus that yaw**, raising one side and lowering the other,
and at the 37.03 target the lean is 1.99 degrees. The yaw is recorded as an
engine finding in `KNOWN_ISSUES.md`, owned by this lane.

**So "in a trunk frame the library's demand is at most 37" is withdrawn.** It
offered a frame **the job does not carry and the consumer cannot resolve**, and
the number in it was contaminated by an unmeasured pelvis rotation. What holds
is narrower: a rotation transmitted in the WORLD frame would ask the consumer
for 65 degrees at that target, and any frame-relative alternative needs a
**trunk-orientation field** the job does not have. That field is now on the
needs list below.

**And the consumer already wrenches its clavicle 68.33 degrees at that target**
(`clavicleTurnedDegrees` in that receipt, the ledger's missing instrument). So
"the width becomes what that rig's anatomy says" is not what A produces there,
and **none of A, B, C or D addresses it**. It is a separate question about a
turned drill and it needs its own measurement.

## No recommendation yet

The first draft recommended A with C as an interim. **That is withdrawn**, and
so is its removal from Marius's list, because the options it chose between were
not the right ones: D was missing, A was costed as one field when it is two,
and the precedent was cited backwards.

What a recommendation now needs:

- **the pivot-position field priced once**, since A and D both need it;
- **a trunk-orientation field priced**, if any frame-relative option is to be
  considered at all, because the job carries no frame and the consumer cannot
  resolve one;
- **the turned drill measured on its own**, and the pelvis yaw settled first,
  since it contaminates every frame-relative number;
- **a decision on whether the 32.72 degrees is a difference to REMOVE or to
  RESPECT** — with D's rest cost on the table, because D moves that difference
  out of the arithmetic and into the consumer's standing pose.

## What the review removed from the first draft, and why it matters

**"The sender is exact" was a tautology.** The first draft's central
measurement was that the engine's clavicle changes length by 0.0001 mm over
every frame of every drill, and read that as proof that the shoulder's motion
"is" a rotation. `l_uparm`'s parent **is** `l_clavicle` in this skeleton, so
that distance is fixed by the rig's own topology. **It would read the same for
any bone on either rig, and it decides nothing.** The 0.0001 mm is float32
noise.

What survives is structural, not measured: because the shoulder is the
clavicle's child, only the **direction** varies — which is an argument for D,
and it comes from the skeleton rather than from a number.

**A statistic was compared against a single reading.** This lane first reported
a "disagreement" with the review's 12.2 degrees, quoting 17.4 to 21.2 from its
own turn-removed measurement. There is no disagreement: 12.2 is **one target**
and the range was **a drill's maximum over all its targets**. Measured at the
same target with the review's own frame definition, this lane reproduces 12.2
exactly. The error was comparing two different quantities under one
description, which is the fault this whole ledger is about.

**A frame was invented, and then MISDIAGNOSED TWICE.** This lane first built a
pelvis frame from the hip line and rebuilt it per frame; it made every drill
*wider*. The first diagnosis was "a hip frame does not remove a trunk turn and
a per-frame rebuild injects the lean". **Both halves are wrong**, and the frame
the paper now uses is the same hip-pinned frame: the hips themselves turn 53.6
degrees at `hooks_outside_hand` frame 0, so a hip frame removes a great deal of
turn, and the widening is the **pelvis yaw** above, not the lean.

**And `trunkTurnDegrees` is not the instrument that draft claimed either.** It
is the AUTHORED track value, `track.turn_at(phase)`, not a measurement of the
solved pose — which is exactly why it reads 0.0 on drills whose solved pelvis is
yawed 15.7 degrees. It is the right quantity for "what was the athlete asked to
do" and the wrong one for "what did the solver produce".

## The instruments

- `scripts/engine_clavicle.py` — the sender's rest geometry, the per-drill
  pivot travel, the rotation ranges in both frames, and the 102 count. **It
  reports a drill it cannot solve rather than skipping it silently**, and
  prints the frame count it visited.
- `scripts/clavicle_divisor_probe.py` — the consumer's residuals, by the
  rendering lane.
- `scripts/engine_targets.py` then `scripts/consumer_residuals.py` — a SECOND,
  independent pair, written by the review of `dae979a` and committed here with
  its attribution. They print the figures this paper quotes that no instrument
  produced before: **32.72 degrees** and its two chords, **52.11 / 31.05**
  against the probe's 52.09 / 31.03, and the **54.72 mm** with the pivot travel
  removed that refuted the decomposition. Run stage one first; it writes
  `engine_targets.json` for stage two.

**Their clone path was a defect and is fixed, not carried.** Both arrived
pointing at the reviewer's own tree. The first attempt to fix that here failed
silently and the pipeline ran against the other tree, writing its results into
this one; the numbers looked right, which is the danger. The path is derived
from the file's location now, the edit that set it asserted before writing, and
the figures above were re-measured from this repository afterwards.

The 102 count is reached by two instruments reading **one source**, the engine's
own definitions; the first draft called that "counted independently", which
overstates it.
