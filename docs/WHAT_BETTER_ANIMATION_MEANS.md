# What better animation means, measurably

Stage 1, item 5 of the character and animation lane, and the brief calls it the
hardest. Written 2026-09-09 against `b1e7bfe`.

The brief asks for a named list of defects, each with an instrument that can see
it, ordered by what a coach would notice first, and says a defect with no
instrument is a judgment and must be labelled one.

**The list is section 4. Section 1 is the reason the list looks the way it
does**, and it is the finding this item turned up.

## 1. The animation receipt measures the FILE, not the MOVEMENT

**MEASURED.** An animated export was run on this branch and this is its receipt's
entire `animation` block, quoted from the file:

    "animation": {
      "frames": 8,
      "framesPerSecond": 5,
      "glb":   { "path": ..., "bytes": 12282344, "sha256": "17f31bc5..." },
      "movie": { "path": ..., "bytes": 145539 }
    }

A frame count, a rate, two sizes and one hash. **Not one measurement of the
motion.**

Compare it with what a phase still carries: a girdle verdict and its miss in
millimetres, a ball anchor error, three arm joint positions per side, a wrist
bend, a forearm roll, a palm normal error, a per-segment clearance for every
digit, a flexion axis report, and a body clearance against the ball.

**So every quality instrument on the rendered figure runs on ONE FRAME.** The
render path measures a pose well and a movement not at all.

## 2. Cross-frame instruments exist, and they are on the other side

**MEASURED.** The repository does measure across frames. It does it on the
SOLVE, in the movement lane's files, before anything is rendered:

| instrument | what it reads |
|---|---|
| `spikes/proof.py:123` | `worstStepBetweenFramesDegrees` and `fastestDegreesPerSecond`, per drill |
| `spikes/retarget.py:111` | `worstStepDegrees` |
| `spikes/measure_seed_variety.py:138` | `worstStep` |
| `spikes/build_library.py` | `phaseSeparation`, whether two graded phases differ |

**This matters for the number the orchestrator is chasing.** The library-wide
worst arm step on the current build is missing, and the orchestrator has asked
the movement lane for it. **The instrument is not missing.** It is
`worstStepBetweenFramesDegrees` in `spikes/proof.py`, and what is missing is a
current run of it across the library. That is worth knowing before anybody
writes a new one.

**The division is clean and it is worth stating plainly.** The solve is measured
through time. The figure is measured a frame at a time. Nothing measures the
rendered movement, which is the thing a coach actually watches.

## 3. How this list was built

A defect earns a row when a coach would see it. It earns an INSTRUMENT column
only when something in this repository can produce a number for it today, and
that instrument is named by file. Everything else is a JUDGMENT and says so.

**Ordering is by what a coach meets first**, which is not the same as severity.
A figure is seen before it moves, and it moves before it is graded.

## 4. The list

### Seen before the figure moves

| # | Defect | Instrument | Owner |
|---|---|---|---|
| 1 | The ball is inside the hand at the release frame | `bodyClearanceMm` in the render receipt, via `scripts/report_clearance.py`. 190 vertices 20.27 mm deep on `chest_pass/release` | rendering, ruled |
| 2 | The kit is not netball kit | **JUDGMENT.** No instrument can read "is this netball kit" | this lane |
| 3 | No cut-out and no contact shadow | **JUDGMENT** | this lane |
| 4 | The rendered shoulders are narrower than the solve asks | `girdle.renderedWidthMm` against `wantedWidthMm`, per phase, in the receipt | movement lane |
| 5 | The figure reads soft where the photograph reads defined | **JUDGMENT**, and it is three-way: phenotype, skin material or light rig. Refer to `WHAT_A_NETBALL_CHARACTER_NEEDS.md` section 4 | this lane |

### Seen while the figure moves

| # | Defect | Instrument | Owner |
|---|---|---|---|
| 6 | An arm jumps between two frames | `worstStepBetweenFramesDegrees`, `spikes/proof.py`. **On the solve, not on the render** | movement lane |
| 7 | The hand is flat through the release and opens after it | `docs/WRIST_AND_PACE.md` measured 22 to 35 degrees of bend, peaking two to four frames AFTER the ball has gone | movement lane, in its retiming unit |
| 8 | The movement plays at the wrong speed | **NO INSTRUMENT, and the quantity has no author.** `frames` is typed in each motion file and nothing derives or measures it. The engine takes 2.24 times the athlete's time on one measured stretch | movement lane |
| 9 | The head does not follow the ball | `orient_head_to_ball` sets it and **nothing reads it back.** No receipt field records where the head ended up | this lane |
| 10 | The figure's motion is not smooth enough to animate | `KNOWN_ISSUES.md` has a per-drill table of worst arm swing. **Its current values are the number in row 6 that nobody has re-run** | movement lane |

### Seen only when the figure is graded

| # | Defect | Instrument | Owner |
|---|---|---|---|
| 11 | Her hand passes close to her face | **NO INSTRUMENT, AND THE ONE THAT WAS BUILT FAILED.** A skull sphere from the head bone's length reported zero hand vertices inside it. A zero from an instrument that cannot reach the face is worse than no zero | this lane |
| 12 | The clavicle is turned further than a clavicle turns | **NO INSTRUMENT.** The clavicle is turned up to 68.33 degrees to follow the girdle and nothing bounds that angle. `KNOWN_ISSUES.md` names it a missing instrument | this lane |
| 13 | The knees differ on drills that ask for nothing asymmetric | the graded checkpoints themselves, and `KNOWN_ISSUES.md` records 15 of 16 below-the-hips checkpoints moving between two solutions | movement lane |
| 14 | A graded phase reads the same as the one before it | `phaseSeparation` in `spikes/build_library.py` | movement lane |

## 5. What the count says

Fourteen rows. **Seven have no working instrument**, counted from the table
rather than estimated:

| row | what is missing |
|---|---|
| 2 | the kit is netball kit: a judgment |
| 3 | the ground and the shadow: a judgment |
| 5 | the figure reads soft: a judgment, and three-way |
| 8 | the pace: no instrument, and the quantity has no author either |
| 9 | the head aim: it is set and never read back |
| 11 | the hand-to-face gap: an instrument exists and returns a false zero |
| 12 | the clavicle elevation: no bound on an angle the renderer computes |

**Six of the seven belong to this lane.** Only row 8, the pace, is the movement
lane's.

**That is the real answer to what better animation means measurably.** Today it
means the seven things it does not mean, because nothing here can see them.

## 6. The instruments this lane would have to build, named

Ordered by what they would unblock, and none of them is built.

1. **A cross-frame instrument on the RENDERED figure.** Every quality number in
   a receipt is per phase. Until one of these exists, "the animation is better"
   is not a claim this lane can make about its own output, only one the movement
   lane can make about the solve. This is the one that changes item 5 from a
   list into a measurement.
2. **A head-aim read-back.** `orient_head_to_ball` aims the head and no receipt
   records the result. It is one number and it would close row 9.
3. **A skull volume that can actually reach the face.** Row 11's instrument
   exists and returns a false zero, which the rendering lane's own handoff calls
   worse than no instrument. Replacing it is not the same as writing one.
4. **A clavicle elevation bound.** Row 12. The angle is already computed to pose
   the bone; nothing compares it with anything.

## 7. What I did not do

- **I did not run `spikes/proof.py`.** The library-wide worst arm step is the
  movement lane's number and the orchestrator has asked them for it. Two lanes
  running the same instrument would produce two figures and a question about
  which is right.
- **I did not build any of the four instruments in section 6.** This is stage 1
  and stage 1 builds nothing.
- **I did not order the list by severity.** It is ordered by what a coach meets
  first, which the brief asked for and which is a different order. Row 11 is
  arguably the worst thing on the list and it is near the bottom.
- **The receipt in section 1 is a sample of one, and I checked what the
  archives hold instead of assuming.** All 21 archived coach receipts carry
  `"animation": null`: 11 in `coach-figures-2413f9d` and 10 in
  `coach-figures-aa3f244`. The coach packs are stills, so **no graded build has
  ever carried an animation measurement of any kind**, and the block quoted in
  section 1 is one I produced today.
