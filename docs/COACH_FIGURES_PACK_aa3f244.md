# Coach figures: the rendering lane's pack

Library `2413f9d`, eleven drills, 48 graded phases, 144 stills, one build stamp,
archived at `.assets/archives/coach-figures-2413f9d` with digest
`d66fc62a0907504e2bd33ca4cc0f6dedc0b7d7fb0cab4a61f9f8b654872049cc`.

This is the first library rendered with the shoulder girdle posed from the
solve. Everything below carries its inputs, because most of these numbers can
only be measured by this lane and an independent reviewer cannot re-derive them
from the engine.

## 1. A finding this lane reported and now withdraws

**The "ball inside the mesh at the release frame" reading was this renderer's,
not the engine's. It is withdrawn.**

This lane reported 150 vertices 17.08 mm inside the ball at the chest pass's
release frame and sent it to the movement lane as a defect in their release. It
is not. The renderer places the wrist by one of two formulae and picks between
them on `ball.holding`:

    target = shoulder + direction * (reachFraction * reach)      # not holding
    target = ball_centre + outward * (radius + wristFromSurfaceInArms * reach)

`holding` goes False AT the release frame, so the formula switches in a single
frame. The two encodings agree to 0.000 mm on the source rig and differ by 19 to
35 mm on this one, because the ball's radius does not scale with the body.
Carrying the grip across the release frame removed 94 and 87 percent of the
depth on the two drills, which is the isolation that settled it.

Two claims made alongside it also fall: the "monotonic 16, 22, 52" reading was
two populations and not one series, and the chest pass was never "a
discontinuity, not a departure" in the engine.

A finding retracted in place is worth more than one deleted, so the original
numbers stay above. The wrist blend-or-pick fix is HELD: it is a contract
ruling, not a defect this lane may settle alone.

## 2. The girdle now follows the solve

The job carries `shoulderShiftFromRestInTorsos`. The renderer resolves it on
its OWN rest girdle, its OWN rest torso and its OWN posed pelvis, so nothing of
the other body's geometry enters.

**The ball's anchor error is the shoulder MIDPOINT error**, because the ball is
`midpoint + fromShouldersInArms * arm` and nothing else in the placement moved.

    passing a 10 mm rule BEFORE the fix     0 of 48
    passing a 10 mm rule AFTER  the fix    46 of 48
    worst remaining      hooks_outside_hand/facing_away   20.45 mm
    the other failure    hooks_outside_hand/contact       11.60 mm

NO PRE-FIX RECEIPTS EXIST, so the BEFORE row is DERIVED from the shipped ones
and not measured from a run. With the girdle at rest the midpoint sat at its
rest position, so the error was the mean transmitted shift resolved on this
body: `|mean(shift.l, shift.r)| * restTorsoM`, both of which every phase
carries. It runs from 33.19 mm at `bounce_pass/release` to 64.05 mm at
`deflect_high/ready`, so none of the 48 was inside the rule.

Both failures are the ONE drill where she is turned, which is the library's only
drill with a real across-body girdle component. On a symmetric drill the two
shoulders miss outward along their own clavicles and those errors cancel in the
midpoint. On a turned drill they do not.

Reproduce from the receipts: every phase carries `girdle.ballAnchorErrorMm`.

## 3. The rendered shoulders are NARROWER than the solve asks

**A shoulder-width reading on these figures is a reading of THE RIG, not of the
solve.** A coach's mark on width lands on the athlete model.

    girdle width the solve asks   290.4 to 339.4 mm
    girdle width rendered         277.4 to 295.8 mm
    narrower by, median            43.98 mm
    narrower by, worst             62.01 mm   hooks_outside_hand/facing_away
    wider by, two phases            1.06 mm   overhead_pass/lift
                                    0.16 mm   overhead_pass/step

An earlier draft of this table said the rendered width ran "277 to 291 mm". It
does not: 25 of the 48 phases exceed 291, the widest being
`bounce_pass/release` at 295.84. The range above is measured from the archived
receipts.

The ball can be right while the girdle is narrow because the two errors cancel
in the midpoint and do not cancel in the width. At `bounce_pass/ready` the left
shoulder misses by 25.473 mm of which 24.084 mm is the ACROSS axis, and the
right mirrors it.

Every phase carries `girdle.wantedWidthMm` and `girdle.renderedWidthMm`.

### Why: the clavicle, with its inputs

A clavicle rotates about its sternal end and does not stretch, so the shoulder
lands on a sphere. Of 102 transmitted targets, 97 sit outside this rig's
sphere and 5 sit inside it. NONE LIES ON IT, so all 102 are out of reach; the
shipped library's 96 read 96 of 96.

    the engine   17.6505 cm / 49.6456 cm = 0.35553 torso lengths
                 `scripts/engine_clavicle.py`: the exporter's own
                 `load_character`, `possession_solve.solve_movement` for the
                 identity, `joint_positions(character, result["identity"])` at
                 REST, joints `l_clavicle` to `l_uparm`, divided by
                 `export_blender_job.rest_torso`. Left and right identical.
    this rig     12.6298 cm / 42.7689 cm = 0.29530 torso lengths
                 `blender_movement_render.rest_girdle`, read on the line after
                 `reset_pose`, bones `clavicle_l` head to `upperarm_l` head,
                 divided by |rest shoulder midpoint - rest pelvis|. Also
                 derivable by one subtraction from `scripts/rest_landmarks.py`.

The engine's clavicle is **20.4 percent longer relative to its torso**, so a
torso-normalised displacement asks a shorter bone to reach further than it can.

Two checks prove the aim is exact and the resolution is not at fault. A ZERO
shift misses by 0.000000 mm. The observed miss EQUALS the radial minimum to
0.0001 mm on all 102 targets, and `girdle.worstBeyondReachableMm` reads
0.00000 on every phase of the shipped library.

**This is a contract question and this lane proposes nothing.** A shoulder's
reachable displacement scales with CLAVICLE length and the field normalises by
TORSO length. A clavicle divisor was measured, not proposed: it reduces the
worst residual from 52.09 mm to 31.03 mm and does NOT remove it, because the two
clavicles differ in rest ORIENTATION as well as in length. So neither divisor is
the whole answer. The instrument is `scripts/clavicle_divisor_probe.py`, which
takes the engine's rest clavicle from `scripts/engine_clavicle.py` and reposes
every phase under both divisors.

## 4. Numbers that are not instruments

**`out of reach` is not evidence that the aim is right.**
`rotate_bone_toward` lands on the radial projection BY CONSTRUCTION, so
`beyondReachableMm` is zero on all 102 targets and the `disagrees` branch cannot
be reached from that caller as the code stands. It is a TRIPWIRE for a later
change that clamps the rotation or moves the pivot, not a check that has passed.
This lane mutation-tested `classify` in isolation and never asked whether its
call site could reach the failing branch. The number that says whether the
FIGURE is right is `ballAnchorErrorMm`, which is not an identity and does fail.

**Every mutation is enumerated, not counted.** An earlier summary said "nine
mutations" and listed none, so the claim could not be checked. The nineteen
pure-python mutations are listed in `tests/test_girdle_agreement.py`'s module
docstring with the guard each one tripped. The renderer's WIRING of those rules
is guarded separately in `tests/test_blender_sources.py`, because an independent
review mutated the call path five ways and left the whole suite green: deleting
the refusal, re-inlining the resolution, dropping `ballAnchorErrorMm`, returning
AGREES for a missing field, and passing the torso where the clavicle's length
belongs. All five now fail, as does a sixth that reintroduces a bare verdict
string.

**The clavicle is turned up to 68.33 degrees** to follow the transmitted girdle,
recorded per side as `girdle.sides.*.clavicleTurnedDegrees`. NOTHING IN THIS
LANE BOUNDS THAT ANGLE. A real clavicle's elevation and protraction are limited
and no instrument here reads them. It is a missing instrument, not a finding.

## 5. A drill that cannot be rendered

`netball_one_hand_high_pass` is ABSENT from this library. Its `ready` phase
cannot be posed:

    FLEXION_AXIS: r index is set to flex about axis 0, which carries only 0.44
    of the turn: x=18.5 y=-7.2 z=42.2 degrees.

**It is not caused by the girdle change.** Posing that phase with the shift
ZEROED raises the identical error with identical numbers, and a zero shift
leaves this rig exactly at its own rest girdle, which is the old behaviour by
this pack's own zero-shift proof. Its other two phases, `lift` and `release`,
pose and pass.

Do not try this by REMOVING the field: at this tip a missing field is refused
by `refuse_unrenderable_girdle` before the hands are posed, so the run stops
with the refusal instead of the flexion error. That refusal is newer than the
first proof.

A first attempt at that proof passed the config's anatomy limits and `None` for
the knuckle limits, where the renderer passes the JOB's own, and reported a
non-reproduction that was its own. The lever is named here because a
non-reproduction is not a result.

A drill the renderer never sees is not a passing drill, so it is counted
nowhere above.

## 6. The sheets, by build

Three columns: before the hand fix, the interim build carrying the clavicle
defect, and the corrected build. **The middle column is not the fix.**

The first column's receipts predate the build stamp, so its build is a CAPTION
and the sheet says so, keeping the receipt reading beside it:

    02b25cd, from the page's own build line. Receipts predate the stamp.
    (captioned, receipts read: UNSTAMPED, predates the build stamp)

Deriving it was tried first and is impossible: the receipts carry a
`jobSha256`, but `spikes/poc-output/` is gitignored and no commit produces
those job files.

## 7. The fan figures

The fan is index tip to pinky tip.

> **REFUTED AND SUPERSEDED, 2026-09-07.** This section said the worst
> left-right gap was 0.095 cm across every phase where both sides appear in
> `grip`. Both halves were wrong: the instrument posed under the CONFIG's
> limits where `render_job` passes the JOB's own, and "both sides appear in
> `grip`" is a label rather than a measurement, so the population included
> holds the job asks to be ASYMMETRIC. `deflect_high/contact`, the phase that
> gave 0.095, is 27.3 degrees off a mirror. Measured on the shipped poses and
> on symmetric holds only, the worst gap is **0.0559 cm** at
> `one_hand_snatch_to_other_hand/pull_in`. Refer to
> `docs/FAN_AND_RELEASE_PACK.md`.

Two phases show gaps above 2 cm, `hooks_outside_hand/contact` at 2.372 and
`one_hand_snatch_to_other_hand/contact` at 2.248. Both look like the old
right-hand defect and neither is: the job carries `grip` for the RIGHT SIDE ONLY
on both, so one hand is closed on the ball near 6.9 cm and the other is open
near 9.3 cm. The instrument narrowed the claim, not the drill names.

These figures have now been re-measured on this library and are no longer held.
The drift figure was also wrong: raising the ball by the overhead pass's own
girdle travel moves the fan by up to 0.3757 cm, not 0.273, which is 6.7 times
the gap the figures report rather than three. The direction of the caution was
right and the size was not. `scripts/fan_mirror_check.py` regenerates them and
proves each pose against the archive.

## 8. The rest-pose difference the fix does not remove

**A figure can pass the acceptance test and still be out fore-and-aft. These
are two different claims.** The guard proves the renderer applied what the solve
sent; it does not prove the pose matches the solve's athlete.

    MHR rest shoulders, ahead of the root    -0.0648 torso lengths
    MPFB rest shoulders, ahead of the pelvis -0.0062 torso lengths
    mismatch                                  0.0586 torso lengths
    on this rig                               2.507 cm

**It is not a landmark convention, and that is proven.** A rigid shift moves
every landmark by the same vector. These do not: shoulder -0.0586, clavicle
+0.1197, neck +0.0551, head +0.0392, a spread of 0.1783 torso lengths with
opposite signs.

**It is not established as posture either, and the pack does not claim it.** The
vertical differences grow steadily with height: shoulder -0.0021, clavicle
-0.0737, neck -0.1481, head -0.2047. A pose does not lengthen a neck. That is a
body PROPORTION difference, and a proportion cannot be posed away, which makes
the bound more permanent than posture would imply.

Reproduce with `python scripts/landmark_comparison.py`.

### The spine bones do not correspond by name

Pairing `spine_03` with `c_spine3` would report 0.3681 torso lengths and read as
an enormous posture finding. It is a naming coincidence. By height the
correspondence is off by one:

    spine_03  0.4866  ->  c_spine2  0.4834     apart 0.0032
    spine_02  0.2765  ->  c_spine1  0.2631     apart 0.0134
    spine_01  0.1174  ->  c_spine0  0.0407     apart 0.0767
    (none)                c_spine3  0.8547     no counterpart on this rig

## 9. Figures only this lane can check

The independent reviewer cannot re-derive the MPFB-side numbers, so their inputs
are here. Each is one division or one subtraction.

    0.9215      48.547 / 52.680        arm chain here over the engine's arm.
                                       Used ONLY to show the ARM divisor was
                                       wrong; it places nothing.
    0.861484    42.7689 / 49.6456      rest torso here over the engine's.
    -0.0062     -0.2648 cm / 42.7689   this rig's rest shoulder, fore-and-aft.
    0.29530     12.6298 / 42.7689      this rig's clavicle, section 3.
    ~6 cm       48.8246 - 42.7681      why shoulder positions in METRES would
                                       raise this rig's ball on every frame.
    4.893 cm    0.11440 x 42.7689      the calibration-phase move under the
                                       ruled displacement form.

`2.23 cm` is the movement lane's, not this lane's: the reading
`chest_pass/ready` would have taken under an arm-length divisor.

`0.8759` is WITHDRAWN. It is not a number this lane has produced, and nobody
cites it.

`19.0 cm` and `12.1 cm` are withdrawn from `HANDOFF_RENDERING.md`: the movement
lane could not confirm them. The rule they illustrated is kept.

## 10. Held, and why

- **`netball_one_hand_high_pass`**, per section 5.
- **The two release stills**, marked "held: ball inside the mesh at the release
  frame, finding open".
- **The fan figure numbers**, until re-measured on this library.
- **The wrist blend-or-pick fix**, and the re-measurement that follows it.
- **The clavicle normalisation**, which is the movement lane's field.

No scapula motion has been invented and no clavicle has been stretched to reach
a number. Where this rig cannot follow the solve, the receipt says so and the
figure carries the miss.
