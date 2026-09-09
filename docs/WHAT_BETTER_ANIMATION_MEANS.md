# What better animation means, measurably

Stage 1, item 5 of the character and animation lane, and the brief calls it the
hardest. Written 2026-09-09, rewritten the same day against `ba98e67` after the
orchestrator ruled that this list splits in two.

The brief asks for a named list of defects, each with an instrument that can see
it, ordered by what a coach would notice first, and says a defect with no
instrument is a judgment and must be labelled one.

**The list is sections 4 and 5, and it is TWO lists.** Section 1 is the finding
that shapes them.

## 1. The animation receipt measures the FILE, not the MOVEMENT

**CAPABILITY.** An animated export was run on this branch and this is its
receipt's entire `animation` block, quoted from the file:

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
render path measures a pose well and a movement not at all. That sentence
survives a new build and a new character, which is why it is capability.

**Checked rather than assumed:** all 21 archived coach receipts carry
`"animation": null`, 11 in `coach-figures-2413f9d` and 10 in
`coach-figures-aa3f244`. **No graded build has ever carried an animation
measurement of any kind.**

## 2. Cross-frame instruments exist, and they are on the other side

**CAPABILITY.** The repository does measure across frames. It does it on the
SOLVE, in the movement lane's files, before anything is rendered:

| instrument | what it reads |
|---|---|
| `spikes/proof.py:123` | `worstStepBetweenFramesDegrees`, `fastestDegreesPerSecond`, per drill |
| `spikes/retarget.py:111` | `worstStepDegrees` |
| `spikes/measure_seed_variety.py:138` | `worstStep` |
| `spikes/build_library.py` | `phaseSeparation`, whether two graded phases differ |
| `.remember/reviews/review-mov5-instruments/review_hips.py` | the pelvis yaw. **Untracked, so no clone has it** |

**The division is clean.** The solve is measured through time. The figure is
measured a frame at a time. Nothing measures the rendered movement, which is
what a coach watches.

**This bears on a number the orchestrator is chasing.** The library-wide worst
arm step on the current build is missing and has been asked of the movement
lane. **The instrument is not missing.** What is missing is a current run of it.

## 3. The rule this list is classified against

Quoted from `docs/CAPABILITY_AND_RESULT.md`, which the content lane wrote and
which merged into main at `74f540a`:

- **CAPABILITY** if every sentence would still be true after a new shoot and a
  new build.
- **RESULT** if it describes what one shoot or one build produced.
- **MIXED** if it holds both, so that a durable sentence and a per-build
  sentence cannot be cited apart.

**Why this split earns its keep here, rather than tidying a file.** A capability
defect cannot be fixed by a better character and a result defect can. Sorting
them says which of stage 2's items are character work and which are boundary
work, and those are different decisions with different costs.

**And the rule found two missing rows on its first application.** The
orchestrator's two worked examples of a result defect were exactly the two this
lane's table lacked. Refer to section 8.

## 4. CAPABILITY: what the pipeline cannot express

Durable. None of these is fixed by a better character, and none of them names a
build because none of them depends on one.

| # | What cannot be expressed | Instrument | Owner |
|---|---|---|---|
| C1 | Any measurement of the rendered MOVEMENT | **NONE EXISTS.** Section 1 | this lane |
| C2 | Where the head ended up | **NONE.** `orient_head_to_ball` aims it at `blender_movement_render.py:601` and again at `blender_mpfb_reference_catch.py:1487`, and no receipt field mentions the head | this lane |
| C3 | Whether a hand passed close to the face | **AN INSTRUMENT EXISTS AND RETURNS A FALSE ZERO.** A skull sphere from the head bone's length reported zero hand vertices inside it. A zero from an instrument that cannot reach the face is worse than no zero | this lane |
| C4 | Whether a clavicle turned further than a clavicle turns | **NONE.** The renderer turns it up to 68.33 degrees to follow the girdle and nothing bounds the angle | this lane |
| C5 | The pace of a movement | **NONE, and the quantity has no author.** `frames` is typed in each motion file and nothing derives or measures it | movement lane |
| C6 | A figure cut out with a contact shadow | **NONE.** The renderer has no shadow catcher and no transparent background | this lane |
| C7 | A wrist, a hand or a finger across the Tactics boundary | The clip contract carries fifteen channels and none of them is a wrist, a hand or a finger | contract lane |
| C8 | A head turn on a delivered character | **The MPFB export carries `Root` and `head`; Tactics asks for `root` and `Head`.** `turnBy` returns on a missing bone, so the head silently never turns. Refer to `THE_FIGURE_AT_THE_TACTICS_BOUNDARY.md` | this lane |
| C9 | Whether the kit is netball kit | **NO INSTRUMENT CAN READ THIS**, and no bib asset exists in the installed library or in any CC0 pack | this lane |

**C8 carries a caveat the others do not.** It is durable only while the delivered
character is an MPFB `game_engine` export. A different rig would have to be
re-checked, and `scripts/tactics_rig_check.py` is the thing that re-checks it.

## 5. RESULT: what this build produced

Per build. **Every row names the build it was seen on, and stops being true when
that build changes.**

| # | What was seen | Figure | Build | Instrument | Owner |
|---|---|---|---|---|---|
| R1 | The ball is inside the hand at the release frame | 190 vertices 20.27 mm deep on `chest_pass/release`; 120 at 17.76 and 78 at 9.55 on the other two release drills; every other phase 20 vertices or fewer at 1.65 mm | `2413f9d` | `bodyClearanceMm`, via `scripts/report_clearance.py` | rendering, ruled |
| R2 | **The fingers do not move, and then they snap open in one frame** | They hold **119.66 to 120.16** through every contact frame, jump **56.2 degrees to 175.87 at the release frame**, then never move again. `spread_fingers` resets the digits once the ball is gone | `1c3d9d7`, `netball_chest_pass`, 96 frames at 60 fps, left hand | the release-hand paper's own measurement | movement lane, in its retiming unit |
| R3 | **The solver yaws the pelvis on drills that author nothing asymmetric** | **10.5 to 24.5 degrees on every square drill**, `chest_pass` **15.7 at all 96 frames**. `docs/CLAVICLE_ARTEFACT.md` records the same magnitude as "the pelvis line holding a magnitude near 15.7 degrees and its sign flipping", and adds that **no parameter has a limit at 15.7 and none was found** | **NOT RECORDED.** Refer to the caution below | `review_hips.py`, untracked | movement lane |
| R4 | The rendered shoulders are narrower than the solve asks | median 43.98 mm, worst 62.01 mm | as recorded in `KNOWN_ISSUES.md` | `girdle.renderedWidthMm` against `wantedWidthMm` | movement lane |
| R5 | An arm jumps between two frames | on `hooks_outside_hand`, worst right upper arm 11.32 degrees at frame 45 | as recorded in `KNOWN_ISSUES.md` | `worstStepBetweenFramesDegrees` | movement lane |
| R6 | The wrist travels after the ball has gone | 22 to 35 degrees of bend through every release, peaking two to four frames AFTER release | `02b25cd` | `docs/WRIST_AND_PACE.md` | movement lane |
| R7 | The engine plays a stretch slower than the athlete | 2.24 times her time, about 45 per cent of her speed | `02b25cd` | `docs/WRIST_AND_PACE.md` | movement lane |
| R8 | The knees differ on drills asking nothing asymmetric | 4.02 to 6.48 degrees on the shipped build; 15 of 16 below-the-hips checkpoints move between two solutions, by up to 20.65 degrees | `32663a9` | the graded checkpoints | movement lane |
| R9 | A graded phase reads the same as the one before it | five checkpoints cannot fail | as recorded in `KNOWN_ISSUES.md` | `phaseSeparation` | movement lane |
| R10 | The figure reads soft where the photograph reads defined | **JUDGMENT, and three-way**: phenotype, skin material or light rig | `9ea602b` | none | this lane |
| R11 | The kit is a grey t-shirt and loose shorts | **JUDGMENT** | `9ea602b` | none. Refer to C9 | this lane |

**R3 CARRIES A CAUTION AND IT IS THIS REPOSITORY'S OWN RULE TURNED ON ITSELF.**
The 10.5 to 24.5 range names no build anywhere it is recorded. The date is
2026-09-07 15:22 and the finder is the clavicle paper's reviewer, but a date is
not a build. `docs/CLAVICLE_ARTEFACT.md` records the 15.7 magnitude against a
transition between `716b3eb` and `ac240b2`, which is a DIFFERENT measurement of
the same phenomenon and must not be quoted as this one's build. **A figure
without its build is exactly what the repository's own audit exists to catch, and
this one is outside the reach of that audit because it is not in `docs/`.**

## 6. The rows that were mixed, and how they split

Three rows of the earlier single list held both halves and could not be cited
apart. Splitting them is the part that changed the shape rather than the filing.

| the old row | its capability half | its result half |
|---|---|---|
| the kit is not netball kit | C9: no instrument can read it, and no bib asset exists | R11: this build wears a grey t-shirt |
| the pace is wrong | C5: `frames` is typed and nothing derives it | R7: 2.24 times her time on `02b25cd` |
| an arm jumps | C1: nothing measures the rendered movement at all | R5: 11.32 degrees at frame 45 |

**The middle one is the clearest case for the split.** A better character fixes
neither half. A re-authored motion file fixes R7 and leaves C5 exactly where it
was, so a lane that fixed the number would believe it had fixed the defect.

## 7. What the count says

**Nine capability rows and eleven result rows.** Counted from the tables rather
than estimated, because a count is a claim about a list.

**Seven of the nine capability rows are this lane's**: C1, C2, C3, C4, C6, C8,
C9. One is the movement lane's (C5, the pace) and one is the contract lane's
(C7, the clip's missing hand). Seven plus one plus one is nine.

Of this lane's seven: **five have no instrument at all** (C1, C2, C4, C6, C9),
**one has an instrument that returns a false zero** (C3), and **one is measured
by an instrument this lane built today** (C8, by `scripts/tactics_rig_check.py`).
Five plus one plus one is seven.

**That is the answer to what better animation means measurably.** Today it means
the seven things it cannot mean, and six of the seven are this lane's to fix
before any of them can be claimed.

## 8. The method fault, recorded because it is the useful part

**Both of the defects the brief named as already recorded were missing from the
first version of this list, and I dropped them silently.**

The brief named "the hand is flat through the release and snaps open in one
frame" and "the pelvis yaws 10 to 24 degrees on drills whose authored turn is
zero". I searched `docs/` for both, found neither, and omitted both without
saying so. They are R2 and R3 above.

**The two failed for DIFFERENT reasons, and only one of them is a search
failure.**

**R2 was outside the repository entirely.** `docs/RELEASE_HAND_PAPER.md` is not
on main, and neither `175.87` nor `56.2` appears anywhere under `docs/` on main.
The paper has sat on an unmerged branch. **No search of the repository could have
found it.** That is a failure of the record, not of the search, and the
orchestrator has taken it.

**R3 was inside the repository under a different name.** `docs/CLAVICLE_ARTEFACT.md`
calls it "the pelvis LINE" and records its magnitude as 15.7. I read that
entry — this lane quoted the knee figures from the section beside it — and did
not connect it, because I was matching the brief's WORDS and the brief's FIGURE
and both differed.

**THE RULE THAT FOLLOWS IS TO GREP FOR THE FIGURE AND NOT THE PHRASE.** `15.7`
finds it in one command where "pelvis yaw" finds nothing. **A number is stable
across vocabularies and a name is not**, which is this repository's own "a name
is not a correspondence" applied to a search rather than to an artefact. The
brief's own "10 to 24" would also have failed; `24.5` would have worked.

**AND THE OBVIOUS FIX TO THE SEARCH RULE IS THE WRONG ONE.** "Search `.remember/`
as well" was this lane's first proposal and it is wrong: **`.remember/` holds
zero tracked files.** Telling every lane to search it would make every lane
depend on local state that no clone has. **A finding a lane must not re-derive
belongs in `docs/`, in git.**

**The honest form of the fault, in one sentence:** the search rule was correct,
one finding was outside the repository, the other was inside it under a different
name, and the only part that was mine was matching on the name instead of the
number.

## 9. The instruments this lane would have to build

Ordered by what they would unblock. None is built and stage 1 builds nothing.

1. **A cross-frame instrument on the RENDERED figure**, closing C1. Until one
   exists, "the animation is better" is not a claim this lane can make about its
   own output — only one the movement lane can make about the solve.
2. **A head-aim read-back**, closing C2. One number, and the renderer already
   computes the aim.
3. **A skull volume that can reach the face**, replacing C3's false zero.
   Replacing a lying instrument is not the same as writing one.
4. **A clavicle elevation bound**, closing C4. The angle is already computed to
   pose the bone and nothing compares it with anything.

## 10. What I did not do

- **I did not run `spikes/proof.py` or `review_hips.py`.** Both are the movement
  lane's and the orchestrator has asked them for the number. Two lanes running
  one instrument produce two figures and an argument about which is right.
- **I did not give R3 a build.** It does not have one recorded and I will not
  invent it from a neighbouring measurement.
- **I did not reclassify any other document.** The orchestrator's ruling
  authorises the rewrite of this document only, and
  `docs/CAPABILITY_AND_RESULT.md` still governs the rest by classifying and
  proposing rather than rewriting.
- **I did not order either table by severity.** They are ordered by what a coach
  meets first, which the brief asked for. C3 is arguably the worst thing here and
  it sits in the middle.
