# The shoulder field sends a position for a joint that has none

A decision paper for Marius, prepared by the movement lane on 2026-09-07.
**It proposes no change and none has been made.** `shoulderShiftFromRestInTorsos`
is unchanged on `main`.

The rendering lane found that its rendered girdle sits about 25 mm per shoulder
narrower than the solve asks. This paper measures why, from both ends, and sets
out the three options with what each would do.

## The measurement, from both ends

**The sender is exact.** Measured by `scripts/engine_clavicle.py` over **every
frame of every drill**, not the graded phases alone:

| quantity | value |
|---|---|
| the engine's rest clavicle | **17.6505 cm** = 0.35553 torso lengths |
| worst change in that length, any frame | **0.0001 mm** |
| the same at a graded phase frame | **0.0000 mm** |
| rotation from rest at the graded phases | 1.2 to **65.5 degrees** |
| travel of the sternal end from rest, relative to the pelvis | up to **6.25 cm** |

**The clavicle is rigid in the solve.** So the shoulder's displacement is
exactly a rotation of a rigid bone about a pivot that itself travels. Nothing
about the sender is approximate.

**The consumer cannot reach it.** Measured by
`scripts/clavicle_divisor_probe.py` on the MPFB rig:

| quantity | value |
|---|---|
| shoulder targets the job transmits | **102** (51 graded phases, both sides) |
| how many lie on that rig's clavicle sphere | **none** |
| worst residual, the ruled TORSO divisor | **52.09 mm** |
| worst residual, a CLAVICLE divisor | **31.03 mm** |
| the two clavicle-to-torso ratios | 0.35553 against 0.29530, **20.4 per cent** |

The 102 is counted independently on each side and agrees.

## Why the field cannot be exact as it stands

A clavicle rotates about its sternal end and does not stretch, so a shoulder's
reachable positions form a **sphere surface** — two degrees of freedom. The
field transmits a **three-vector position**. A position off that surface is not
a pose the consumer's anatomy can adopt, and 102 of 102 are off it.

**A divisor cannot fix that.** Any divisor scales the vector, and scaling
changes its length, not its direction. So a divisor moves a target along the
line from the pivot and can only reach the sphere if the direction is already
right. The two rigs' rest clavicle orientations differ, so it is not.

That is exactly what the probe measures: the clavicle divisor removes
**21.06 mm** of the 52.09 — the part the length difference explains — and
leaves **31.03 mm**, which is the orientation difference. A scalar buys the
first and cannot touch the second.

## The three options

### A. Transmit a clavicle rotation

**What changes.** The field sends the rotation from the consumer's own rest
clavicle direction to the posed one, and the pivot's own displacement, which
the existing pelvis-relative machinery already carries.

**The 102 targets.** Every one lands **on** the consumer's sphere by
construction, whatever its bone length or rest orientation. The reachability
residual becomes zero, not smaller.

**The girdle width.** It becomes the consumer's own clavicle length at the
transmitted rotation — what that rig's anatomy says. The 25 mm per shoulder
stops being an error and becomes the rig's honest width.

**What it costs.** A rotation needs an axis convention, which is a real cost
and not a new problem: `knuckleLimitsDegrees` faced it and was settled the same
way, as rotations about each joint's **own** axes resolved in the consumer's
frame. The precedent is in this repository and the handoff already carries the
rule.

**What it loses.** Nothing on the sender's side, and the 0.0001 mm is the
proof: a rigid bone's motion is fully described by a rotation and its pivot.

### B. Normalise by clavicle length

**The 102 targets.** Worst residual 52.09 → **31.03 mm**. Still none of them on
the sphere.

**Why it stops there.** A scalar cannot correct an orientation, as above.

**What it costs.** A fourth divisor in a job that already carries three, and it
would still transmit a position for a joint that has none. It buys 40 per cent
of the error and keeps the shape that caused it.

### C. Keep the field; the consumer projects onto its own sphere, and the contract says so

**The 102 targets.** Every one lands on the sphere, by the consumer's own act.

**What it costs.** Nothing in the contract, and the field just shipped. But the
projection moves each target by up to **52.09 mm** in a direction the engine
never chose, and the decision moves from the sender, which knows what the
shoulder was doing, to the consumer, which does not. It is the cheapest and the
least honest.

## The recommendation

**A is the only exact option and the right shape.** The sender's own geometry is
a rigid-bone rotation, measured to a ten-thousandth of a millimetre, so a
rotation is not an approximation of the engine's meaning — it **is** the
engine's meaning, and the current field is the approximation.

**B should be rejected on the measurement.** It buys 21 of 52 mm and adds a
divisor to keep a shape that cannot be exact.

**C is the correct interim** if A cannot be scheduled soon. It costs nothing,
its error is bounded and now measured, and it can be stated in the handoff in
one paragraph. It must be written down as an interim rather than an answer.

## What none of the three fixes

The **~2.5 cm fore-and-aft rest-posture residual** already recorded against the
shoulder field is a different thing and survives all three. Neither lane can
separate a landmark convention from a posture there: MPFB has no `root` bone
and this lane has no MPFB rig.

## The instruments

Both are committed and both re-run their own numbers.

- `scripts/engine_clavicle.py` — the sender's rest geometry, the rigidity over
  every frame, the rotation range, the pivot travel, and the 102 count.
- `scripts/clavicle_divisor_probe.py` — the consumer's residuals, by the
  rendering lane.
