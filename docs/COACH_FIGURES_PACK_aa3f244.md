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
