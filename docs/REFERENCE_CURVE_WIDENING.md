# Widening the reference curves to what the library actually grades

A design. **Nothing here is executed**, and it cannot be until the shared MHR
assets are restored, because regenerating the curves needs a solve.

## The finding

`export_reference_curves.WANTED` is five measures:

    leftElbowFlexionDegrees, rightElbowFlexionDegrees,
    leftShoulderElevationDegrees, rightShoulderElevationDegrees,
    trunkLeanDegrees

They were chosen for a stated reason, and the file says so: "the measures a
two-camera lift can plausibly recover". That was the right question for the
video spike. **It was never reconciled with what the coaching layer grades.**

Asked of the definitions themselves, via the new
`MovementDefinition.graded_measures()`:

| measure | drills grading it | in `WANTED` |
|---|---|---|
| `leftKneeFlexionDegrees` | **8 of 8** | **no** |
| `leftElbowFlexionDegrees` | 7 of 8 | yes |
| `trunkLeanDegrees` | 7 of 8 | yes |
| `rightElbowFlexionDegrees` | 6 of 8 | yes |
| `leftShoulderElevationDegrees` | 5 of 8 | yes |
| `rightShoulderElevationDegrees` | 2 of 8 | yes |
| `footHeightGapCm` | 1 of 8 | **no** |
| `rightKneeFlexionDegrees` | 1 of 8 | **no** |
| `trunkTurnDegrees` | 1 of 8 | **no** |

**The measure graded by every drill in the library has no reference curve.**
Nothing in `WANTED` is wasted — all five are graded — but four graded measures
are missing, and the most-graded of all is one of them.

## The design

**Take the union of `graded_measures()` across the library, and keep the five
already there.** Not "replace `WANTED` with the graded set": `WANTED`'s own
question is still a good one, and a measure a lift can recover is worth a
reference curve even if no checkpoint reads it today. The rule is *graded OR
recoverable*, and today that is nine measures.

Derived, not typed. A definition that starts grading a tenth measure should get
its curve without anyone remembering to edit a list, which is the whole failure
this is repairing.

### The unit field is not optional

`footHeightGapCm` is **centimetres**. The file's own note says "Angles are the
engine's own definitions", and every consumer to date has read every column as
degrees. Adding a centimetre column to a file that announces itself as angles
is the units-across-a-boundary fault this project has recorded six times, and
it would be introduced deliberately.

So each curve carries its unit:

```json
"curves": {
  "leftKneeFlexionDegrees": {"unit": "degrees", "values": [...]},
  "footHeightGapCm":        {"unit": "centimetres", "values": [...]}
}
```

That is a **breaking change** to the file's shape: today `curves[measure]` is
the list itself. The alternatives were considered and rejected —

- *Keep the flat shape and exclude `footHeightGapCm`.* The one measure whose
  unit differs is dropped precisely because its unit differs, which is how a
  file stays tidy and a library stays ungraded.
- *Keep the flat shape and infer the unit from the name suffix.* `...Degrees`
  and `...Cm` do currently say it. Inferring a unit from a naming convention is
  a convention two people must hold, and this document exists because a
  five-item list drifted from a nine-item one.

`schemaVersion` rises with the change, and the note stops claiming everything
is an angle.

### The regeneration plan

Regenerating is a solve, so it is **stamped on the build that runs it** and
that build is recorded in the file, as `generatedFrom` already does.

1. The assets are restored and the solver runs again. Nothing below can start
   before that.
2. Land the shape change with `WANTED` still five measures. The file's shape
   changes, its content does not, and consumers migrate against a diff that is
   only a shape.
3. Widen to the derived set in a second pass. Now the content changes and the
   diff is only new columns.
4. Regenerate on a clean tree and check `generatedFrom.treeWasClean`.
5. Tell the video lane the new columns and their units, because they are the
   consumer and the boundary is theirs as much as ours.

Two passes rather than one because a shape change and a content change landing
together give a reviewer no way to tell which caused what.

### What this does not settle

- **Whether a two-camera lift can recover a knee at all.** The video spike's
  answer was that no angle was gradeable from that footage. A reference curve
  for the knee is worth having regardless — it is the engine's half of a
  comparison — but nobody should read its existence as a claim that the video
  side can produce the other half.
- **`footHeightGapCm` is a magnitude with a floor of zero**, and its bands are
  two of the five cannot-fail phases recorded in `docs/KNOWN_ISSUES.md`. Its
  curve is honest; the checkpoints reading it are the open question.

## Executed, and what the new columns actually contain

Both passes landed on 2026-09-01: the shape in `1d0721e`, the content in
`d757637`. Five measures became nine. The design above stands as written, with
one addition it did not anticipate.

**The rule moved out of the exporter into `reference_measures.py`, and that is
not tidiness.** The exporter imports the solver, so a rule living there cannot
be called by a test on a machine without one. A mutation replacing the derived
set with the old five survived every test while the rule sat in the exporter.

### Two of the four new columns are constant on most drills

Read on `24cc9bc`, over the eight drills that carry a ball and a technique.

| measure | varies on |
|---|---|
| `leftElbowFlexionDegrees` | 8 of 8 |
| `rightElbowFlexionDegrees` | 8 of 8 |
| `leftShoulderElevationDegrees` | 8 of 8 |
| `rightShoulderElevationDegrees` | 8 of 8 |
| `trunkLeanDegrees` | 8 of 8 |
| `leftKneeFlexionDegrees` | 8 of 8 |
| `rightKneeFlexionDegrees` | 8 of 8 |
| `footHeightGapCm` | **3 of 8** |
| `trunkTurnDegrees` | **1 of 8** |

`trunkTurnDegrees` is the athlete's facing along the drill's track, and only
`hooks_outside_hand` turns, from 4 to 48 degrees. `footHeightGapCm` is flat at
0.00 wherever both feet are level, which is five of the eight.

**A flat curve is an honest reference for a drill where the quantity does not
move.** It is not an export defect. A consumer should test the minimum against
the maximum before treating agreement with a flat curve as evidence, and the
exported file's own note now says so.

The note says it WITHOUT the counts above, on purpose. A count in prose is a
figure with no instrument on it, and five of those went stale in
`docs/KNOWN_ISSUES.md` this same morning. The note states the shape of the
thing, which cannot go stale. The counts are here, and they name the build
they were read on.

`trunkTurnDegrees` is also the one measure `video_measures` marks NOT
CARRIABLE: the lift describes a pose, not a position in the gym. Its curve is
the engine's half of a comparison whose other half video cannot supply.
