# Retiming the carry moves the graded window. The easing does not.

Measured on 2026-09-09 against `13148a7`. The instruments are
`scripts/sweep_carry_timing.py` and `scripts/sweep_release_easing.py`, both
committed. `spikes/movements/` is copied to a temporary directory and patched
there; the repository's own files are never written.

**This is the number Marius's ruling assumed and nobody had taken.** He ruled the
release timing mechanical on the condition that it lands before Erin grades,
because a retiming moves the arm inside the frames her checkpoints measure.
**That is now measured, and he was right.**

## What was varied, and why it authors nothing

Each pass's technique file carries an `afterContact` path. The last key is the
release. **Moving the key before it LATER compresses the same travel into fewer
frames before the release**, which is what "the hand accelerates into the
release" means in the numbers the engine already has.

| drill | key moved | shipped | release |
|---|---|---|---|
| `chest_pass` | `drive` | 0.62 | 0.80 |
| `overhead_pass` | `step` | 0.58 | 0.80 |
| `bounce_pass` | `drive` | 0.62 | 0.80 |
| `one_hand_high_pass` | `step` | 0.55 | 0.80 |

Swept at **−0.25, 0.0, +0.25, +0.50, +0.75** of the gap to the release, so the
shipped build sits **inside** the range and not at its end. One existing number
per drill. **Nothing is created.**

**The chest pass's `step` key is deliberately not touched.** Its own note reads
"SHE STEPS AND THE BALL DOES NOT MOVE … the manual's 'Keep hands where they were
with catch, don't pull ball back' … NOTHING GRADES IT". It is authored coaching
intent, and a retune that accelerated the whole carry would delete a manual cue
that no instrument would catch.

## The result: one checkpoint per drill, and it moves a great deal

| checkpoint | −0.25 | +0.25 | +0.50 | +0.75 |
|---|---|---|---|---|
| `bounce_pass/drive/leftElbowFlexionDegrees` | −6.01 | +7.24 | +14.65 | **+22.02** |
| `chest_pass/drive/leftElbowFlexionDegrees` | −4.45 | +5.15 | +10.21 | **+14.95** |

**Both are monotonic in the shift.** That is the signature this sweep exists to
distinguish: **a dose-response, not a basin.** The easing sweep's large rows
appeared and disappeared as the parameter moved; these grow with it in both
directions, including the negative one.

**Up to 22 degrees at the bounce pass's drive phase, against a 5.0 degree band
floor.** That is four band floors.

## Against this sweep's own null

The largest move in a phase the change **cannot reach** — `ready` and `step`,
which precede the moved key — is **6.00 degrees**, on
`one_hand_high_pass/ready/leftKneeFlexionDegrees`. That row has no effect present
to contaminate it, so it is this sweep's own noise.

**The null is large, and it is honest to say so.** It is three times the easing
sweep's 1.71, and it sits on the same drill's ready knee, which was the noisiest
row there too. The lower body is discontinuous in its inputs and this measures
that again.

**The two drive-phase rows clear that null by three to four times AND are
monotonic.** Nothing else in the sweep clears it at all.

## Why only two drills respond

**A checkpoint moves when it is graded AT the phase whose key moved.** The chest
and bounce passes both grade an elbow at a `drive` phase, and `drive` is the key
that moved on both. The overhead and one-hand-high passes moved a `step` key and
grade a knee at `step`, and those moved 0.63 and 0.46 — inside the null.

So the effect is not "retiming moves everything". It is **precise and local: it
moves the elbow at the phase being retimed.**

## The two decisions, now measured and genuinely different

| | what it varies | largest graded move | against its own null | shape |
|---|---|---|---|---|
| **the easing** | the follow-through after the release | 8.40 | 1.71 | **non-monotonic**, a basin |
| **the carry timing** | the drive key before the release | 22.02 | 6.00 | **monotonic**, a dose-response |

**The easing is outside her window and the carry is inside it.** That is what
Marius's ruling assumed, and both halves are now measured rather than argued.

**His condition is correct and necessary.** A retimed build changes an elbow
Erin grades by up to 22 degrees. If it lands after she grades, she has graded a
build the engine no longer is.

## What this does NOT say

**It does not say the retiming is right.** It says it is visible. Whether the
elbow SHOULD read 15 degrees more at the drive phase is a coaching judgment, and
`leftElbowFlexionDegrees` at `drive` has a band that a retimed value may leave.

**It does not test an accelerating carry against the release seam.** That was the
orchestrator's hypothesis and it needs the follow-through measured alongside a
retimed carry, which is a second run.

**And it does not license a retune.** No number under `spikes/movements/` is
changed by any of this. Gate 4 stands and the shape of the retiming is a
coaching judgment nobody has made.
