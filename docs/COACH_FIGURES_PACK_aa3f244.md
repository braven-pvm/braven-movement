# Coach figures: the rendering lane's pack

DRAFT. The figures are HELD pending the shoulder-anchor fix. Everything below
the figure slots is settled and reproducible. The slots are marked and empty on
purpose, because a figure staged before the fix is a figure to withdraw.

Build: renders archived at `aa3f244`. Measurements taken 2026-09-04 against the
`aa3f244` job export, renderer commits `aa2425a` to `bc95caf`.

## 1. A finding this lane reported and now withdraws

**The "ball inside the mesh at the release frame" reading was this renderer's,
not the engine's. It is withdrawn.**

This lane reported 150 vertices 17.08 mm inside the ball at the chest pass's
release frame, and sent it to the movement lane as a defect in their release.
It is not. `blender_movement_render.py` places the wrist by one of two
formulae, and picks between them on `ball.holding`:

    holds = bool(grip) and side in grip
    target = shoulder + direction * (reachFraction * reach)      # not holding
    target = ball_centre + outward * (radius + wristFromSurfaceInArms * reach)

`holding` goes False AT the release frame, so the formula switches in a single
frame. The two encodings agree to 0.000 mm on the source rig and differ by 19
to 35 mm on this one, because the ball's radius does not scale with the body.
The switch happens at exactly the frame where they differ most.

Isolating it confirmed the attribution: carrying the grip across the release
frame removed 94 percent and 87 percent of the depth on the two drills. The
engine's release is not a departure. This renderer's wrist formula is a
discontinuity.

A finding retracted in place is worth more than one deleted, so the original
numbers stay above. Two claims made alongside it also fall: the "monotonic 16,
22, 52" reading was two populations and not one series, and the chest pass was
never "a discontinuity, not a departure" in the engine.

The wrist blend-or-pick fix is HELD. It is a contract ruling, not a defect this
lane may settle alone.

## 2. The ball is anchored to a landmark the job does not transmit

The full entry is in `docs/KNOWN_ISSUES.md`. In short: the ball is placed at
`shoulders + fromShouldersInArms * arm`, every term is transmitted except
`shoulders`, and this renderer never poses a clavicle. Its shoulder midpoint
sits 42.7681 cm above the pelvis on all 43 graded phases of all 10 drills,
range 0.0000. The engine's moves on every drill.

**15 of 43 phases pass a one-centimetre rule. 28 fail. 19 of the failures are
HELD phases, where the ball is in her hands.** Every drill in the library has at
least one failing phase. Worst is `overhead_pass/lift` at 8.451 cm, which is 77
percent of the ball's radius.

Reproduce with `python scripts/ball_anchor_verdict.py`.

Two corrections this lane made to its own numbers, both kept on the record:

- The first table was VERTICAL ONLY and understated by a whole tolerance.
  `overhead_pass/lift` is 8.451 cm, not the 7.41 first published, because 4.08
  cm of it is fore-and-aft.
- The field was specified from reasoning three times before it was measured.
  Metres, then arm lengths, then torso lengths, then displacement from the rest
  pose. Each correction came from a measurement.

`girdle_agreement.py` is the consumer guard. It reports a missing field as
`unavailable` and never as agreement, because the whole defect was a missing
field behaving like a satisfied one.

### What the fix does NOT remove: a 2.5 cm rest-pose difference

**A figure can pass the acceptance test and still be up to 2.5 cm out
fore-and-aft. These are two different claims and the pack must not merge them.**

The acceptance guard compares this rig's RENDERED girdle displacement against
the TRANSMITTED one, inside this body. It proves the renderer applied what the
solve sent. It does not prove the resulting pose matches the solve's athlete,
because the two rigs' rest poses are not the same body in the same pose.

**IT IS NOT A LANDMARK CONVENTION, AND THAT IS PROVEN.** A rigid shift of the
origin moves every landmark by the same vector. Comparing the two rest poses in
torso lengths, the fore-and-aft differences are:

    shoulder    -0.0586        neck    +0.0551
    clavicle    +0.1197        head    +0.0392

A spread of 0.1783 torso lengths, 7.6 cm on this rig, with opposite signs. No
translation produces that. The argument needs no correspondence between the two
skeletons, which is why it holds despite everything below.

**WHETHER IT IS POSTURE OR BUILD IS NOT SETTLED, and the pack does not claim
posture.** The vertical differences grow steadily with height:

    shoulder    -0.0021    clavicle    -0.0737
    neck        -0.1481    head        -0.2047

A pose does not lengthen a neck. That pattern is a body PROPORTION difference,
and a proportion difference cannot be posed away. Posture is the more hopeful of
the two readings and this data does not support choosing it.

The clavicle is the largest single difference and it has not been examined. From
the sternal end to the shoulder, the engine's clavicle sweeps 0.1928 torso
lengths backward and this rig's sweeps 0.0145. The two chests are not laid out
the same way.

Consequences a reader must have:

- On the calibration phase this rig's girdle moves **4.893 cm forward**. That
  follows the solve and is correct, given the transmitted displacement.
- A residual fore-and-aft uncertainty of about **2.5 cm at every phase**
  remains. That is 2.5 times the one-centimetre rule and 23 percent of the
  ball's radius.
- No figure is described as accurate to better than 2.5 cm in that axis.

### The spine bones do not correspond by name

Pairing `spine_03` with `c_spine3` would report 0.3681 torso lengths of
difference and read as an enormous posture finding. It is a naming coincidence.
By height the correspondence is off by one:

    spine_03  0.4866  ->  c_spine2  0.4834     apart 0.0032
    spine_02  0.2765  ->  c_spine1  0.2631     apart 0.0134
    spine_01  0.1174  ->  c_spine0  0.0407     apart 0.0767
    (none)                c_spine3  0.8547     no counterpart on this rig

Reproduce with `python scripts/landmark_comparison.py`.

### Figures in this pack that only this lane can check

The independent reviewer could not test the MPFB-side numbers, so their inputs
are here beside them. Each is one division or one subtraction.

    0.9215      48.547 / 52.680        arm chain here over the engine's arm.
                                       Used only to show the ARM divisor was
                                       wrong; it is not used to place anything.
    0.861484    42.7689 / 49.6456      rest torso here over the engine's. This
                                       is the resolution scale.
    -0.0062     -0.2648 cm / 42.7689   this rig's rest shoulder, fore-and-aft,
                                       in torso lengths.
    ~6 cm       48.8246 - 42.7681      why shoulder positions in METRES would
                                       raise this rig's ball on every frame.
    0.65 cm     42.7689 - 42.1153      the neutral move under the withdrawn
                                       POSITION form. 42.1153 is 48.8867 x
                                       0.861484.
    4.893 cm    0.11440 x 42.7689      the calibration-phase move under the
                                       ruled DISPLACEMENT form. 0.11440 is
                                       (2.4622 + 3.2170) / 49.6456.
    1.1 to      Bruce's three-axis     every phase resolved onto this rig's
    5.8 cm      table x 0.861484,      span (0, 42.7681, -0.2648). The evidence
                minus this rig's span  that POSITIONS cannot cross bodies.

`2.23 cm` is not this lane's figure. It came from the movement lane, as the
reading `chest_pass/ready` would have taken under an arm-length divisor.

`0.8759` is not a number this lane has produced. If it is attributed here,
someone must say where it was used before it is relied on.

## 3. The sheets, by build

Three columns: before the hand fix, the interim build carrying the clavicle
defect, and the corrected build. **The middle column is not the fix.**

The first column's receipts predate the build stamp, so its build is a
CAPTION and the sheet says so, keeping the receipt reading beside it:

    02b25cd, from the page's own build line. Receipts predate the stamp.
    (captioned, receipts read: UNSTAMPED, predates the build stamp)

Deriving it was tried first. The receipts carry a `jobSha256`, so a matching
job file in git would have named the commit outright, but `spikes/poc-output/`
is gitignored and no commit produces those job files.

> FIGURE SLOT: sheets for every drill, on the re-rendered library.

## 4. The fan figures

HELD, and the reason is measured rather than assumed. Posing every phase a
second time with the ball raised by the overhead pass's own girdle travel of
7.40 cm moves the fan by up to 0.273 cm, because the fingers flex until they
reach the ball surface. The mirror gap the figures would REPORT is 0.095 cm. A
pending fix that can move the published number by nearly three times the number
itself makes any figure staged now a figure to withdraw.

The claim itself needed narrowing, and the instrument narrowed it rather than
the drill names. Two phases show fan gaps above 2 cm, `hooks_outside_hand/
contact` at 2.372 and `one_hand_snatch_to_other_hand/contact` at 2.248. Both
look like the old right-hand defect and neither is: the job carries `grip` for
the RIGHT SIDE ONLY on both, so one hand is closed on the ball near 6.9 cm and
the other is open near 9.3 cm. **Across every phase where both sides appear in
`grip`, the worst gap is 0.095 cm.**

> FIGURE SLOT: fan figures, measured after the fix.

## 5. Numbers in the docs measured on older builds

`out/pack-aa3f244/docs-number-audit.md`, regenerated by
`scripts/docs_number_audit.py`. 120 rows that a render receipt can re-measure,
with the document, the line, the numbers, the section's build, and the receipt
field that answers each one. Six name no build at all, which is the worse case.
11 touch the lower body and are MARKED, not dropped, because nothing below the
hips may be refreshed into a graded value.

Nine of the fifteen originally unattributed rows were this lane's own, added the
same morning. They are attributed now.

Each lane refreshes its own documents. This list is the instrument, not an edit.

## 6. Held, and why

- **Every re-render.** The library, not four drills. Every drill has a failing
  phase, and `bounce_pass` has no job file at all, so it must be exported on the
  fixed main during the re-render.
- **The two release stills**, marked "held: ball inside the mesh at the release
  frame, finding open".
- **The fan figure numbers**, per section 4.
- **The wrist blend-or-pick fix**, and the re-measurement of the divergence that
  follows it.

No scapula motion has been added to the renderer. Inventing a girdle pose the
job does not carry would put a pose in the figures that no solve produced,
which is the fault this pack reports.
