# The figure as it is

Stage 1, item 1 of the character and animation lane. Read on 2026-09-09 against
main `13148a7`. Nothing here is built and nothing is proposed. Every claim names
where it was read.

This lane is new. The figure was read from the code, from the receipts of the
graded build `2413f9d`, and from the stills of that same build. Where a claim is
a judgment and not a measurement, it says so.

## 1. The path, end to end

Seven stages. The first three are the movement lane's, and they are named here
only so the boundary is visible.

1. **The solve.** `spikes/possession_solve.py` solves the movement on the MHR
   character. This lane does not touch it.
2. **The job.** `spikes/export_blender_job.py` writes one `*.job.json` per
   movement. That file is the entire interface. Nothing absolute crosses it
   except the ball radius, because the MPFB athlete is not the size of the
   athlete the engine solves on. Reach is in arm lengths, stance is in leg
   lengths, the ball offset is in arm lengths, and the shoulder shift is in
   torso lengths.
3. **The camera.** The three views are a constant in that same file: front at
   `[0.0, -3.20, 1.10]`, quarter at `[2.20, -2.35, 1.20]`, side at
   `[3.20, -0.15, 1.10]`. All are 50 mm, all are 1080 x 1350 pixels.
4. **The athlete.** `blender_mpfb_reference_catch.py` `create_athlete` builds
   her. Refer to section 2.
5. **The pose.** `blender_movement_render.py` `pose_phase` poses that rig from
   one phase of the job. Refer to section 4.
6. **The picture.** The same file renders three views of each graded phase. On
   `--animate` it also exports a GLB and a video.
7. **The receipt.** `<movementId>.render.json`, beside the images. Refer to
   section 5.

`spikes/export_manual_page.py` then assembles the manual page from the stills
and the receipts. It solves nothing, poses nothing and renders nothing.

## 2. There is no model file, and that answers "which model file"

The character is not loaded from a file. She is generated on every run from
numbers in `config/reference_catch.v1.json`:

    HumanService.create_human(macro_detail_dict=macro)
                                          blender_mpfb_reference_catch.py:1085

The macro is the nine phenotype values in that config: `age` 0.32,
`cupsize` 0.28, `firmness` 0.84, `gender` 0.0, `height` 0.72, `muscle` 0.88,
`proportions` 0.52, `weight` 0.31, and `race` caucasian 1.0, african 0.0,
asian 0.0.

Seven MPFB assets are then added by path, and each one is a file:

| slot | asset |
|---|---|
| skin | `skins/young_caucasian_female/young_caucasian_female.mhmat` |
| kit | `clothes/female_casualsuit02/female_casualsuit02.mhclo` |
| shoes | `clothes/shoes05/shoes05.mhclo` |
| hair | `hair/ponytail01/ponytail01.mhclo` |
| eyes | `eyes/high-poly/high-poly.mhclo` |
| eyebrows | `eyebrows/eyebrow006/eyebrow006.mhclo` |
| eyelashes | `eyelashes/eyelashes01/eyelashes01.mhclo` |

The kit's material is then replaced by `make_fabric_material`, so the grey is
this repository's and not the asset's. The expression is seven Faceunits 01
targets, named in the same config.

**The consequence for this lane.** A new character is a change to nine numbers
and seven asset paths. It is not a new mesh to import. That is the cheapest
possible place to change her, and it is why item 3 of the brief must be answered
before anything is built.

## 3. The rig

    rig = HumanService.add_builtin_rig(human, "game_engine", import_weights=True)
                                          blender_mpfb_reference_catch.py:1099

MPFB's built-in `game_engine` rig, renamed `BRAVEN_Athlete_Rig`. The bone names
the poser uses are `pelvis`, `neck_01`, `upperarm_{l,r}`, `lowerarm_{l,r}`,
`hand_{l,r}`, `thigh_{l,r}`, `calf_{l,r}` and `foot_{l,r}`.

**It has 30 finger bones and no metacarpal.** `docs/HANDOFF_RENDERING.md` says
so, and says why the word must not be used: MHR's equivalent segment is
wrist-to-knuckle, and the rest bend differs per digit AND per rig.

**This rig cannot reach the girdle the solve asks for.** Of 102 transmitted
shoulder targets, none lies on this rig's clavicle sphere. The rendered girdle
is a median 43.98 mm narrower than the solve asks, and 62.01 mm narrower at
worst. The mechanism is a build difference: the engine's clavicle is 0.35553
torso lengths against this rig's 0.29530. Read in `docs/KNOWN_ISSUES.md`, first
entry. **A shoulder-width reading taken off a rendered figure is a reading of
this rig, and not of the solve.**

## 4. How a solved pose reaches the figure

`pose_phase` in `blender_movement_render.py:499`, in this order. The order is
load-bearing.

1. Reset to rest. The rest girdle is read here and nowhere later.
2. Pose the stance from `stance.ankleFromPelvisInLegs`.
3. Pose the girdle from `shoulderShiftFromRestInTorsos`, resolved on this rig's
   own rest torso. It moves BEFORE the ball is placed, because the ball is
   placed from the shoulder midpoint.
4. Refuse the phase if the girdle field is missing. A missing field renders the
   pre-fix figure, and it would otherwise print PASS.
5. Place the ball at `shoulders + fromShouldersInArms * armLength`.
6. Aim each arm. **The wrist target comes from one of two formulae, per hand,
   selected on whether that hand holds the ball.** Free: from the shoulder along
   `direction`. Holding: from the ball centre along `outward`. This switch
   causes the worst figure defect in section 7.
7. Orient each hand, curl the fingers, and measure the clearance per digit.
8. Turn the head to the ball.

## 5. What the receipt records

Read from the receipts of the graded build, and not from the code alone:
`.assets/archives/coach-figures-2413f9d`, digest
`d66fc62a0907504e2bd33ca4cc0f6dedc0b7d7fb0cab4a61f9f8b654872049cc`.

Per drill, at the top level:

    movementId, skill
    generatedFrom   commit, treeWasClean, utcTimestamp
    jobSha256       the job that was posed
    sourceAssets    the MPFB asset paths
    animation       null unless --animate
    phases[]        the phases that drew
    failedPhases[]  the phases that could not, each with its reason

Per phase: `name`, `frame`, `ballCentreM`, `holding`, `stance`, `girdle`
(`verdict`, `restTorsoM`, `worstOffsetMm`, `ballAnchorErrorMm`,
`renderedWidthMm`, `wantedWidthMm`, and each side), `arms` (the shoulder, elbow
and wrist positions per side), `hands` (`wristBendDegrees`,
`forearmRollDegrees`, `palmNormalErrorDegrees`, `surfaceClearanceMm` per digit
per segment, and `flexionAxis`), `bodyClearanceMm`, and `views` with each
image's path, bytes, **sha256**, width, height, lens and corner colours.

`render_receipt.py` decides the word the run prints. `PASS` only when something
was produced and nothing failed. `NOTHING RENDERED` when no phase was posed and
no animation was exported. `SOME PHASES FAILED` outranks both.

**`failedPhases` is absent from the `2413f9d` receipts.** The key is newer than
that build. A reader that predates it sees a short `phases` list and no cause.

## 6. What the receipt does not record, and it is this lane's to fix

> **FIXED ON THIS BRANCH, after the orchestrator approved it on 2026-09-09.**
> `asset_licences.py` holds the two determinations, quoted from
> `docs/LICENSING.md`. The receipt now records path, sha256 and licence per
> asset, and an asset with no determination stops the run in
> `Studio.__init__`, before any figure is drawn. The reading below is kept as
> the record of the defect. Refer to section 10 for what the fix does and what
> it deliberately does not do.

**The movement render receipt names its source assets by path, and never hashes
them.**

    "sourceAssets": [str(path) for path in studio.source_assets],
                                              blender_movement_render.py:899

The reference generator builds the same athlete from the same assets, and it
does hash them:

    "assets": [{"path": str(path), "sha256": sha256(path)} for path in source_assets]
                                          blender_mpfb_reference_catch.py:1687

Three things follow, and all three matter to this lane's MVP.

1. **`docs/ARCHITECTURE.md` rule 7 is not met by this receipt.** The rule
   requires a generated receipt to record source-asset hashes, including the
   Faceunits pack manifest. The receipt behind every coach figure records paths
   only.
2. **A path is not an identity.** The recorded paths point into a named user's
   Blender profile, for example
   `...\Blender\4.5\extensions\.user\blender_org\mpfb\data\clothes\female_casualsuit02\female_casualsuit02.mhclo`.
   If MPFB is updated, the same path names different bytes, and no receipt can
   tell the two builds apart. This repository already has a rule for exactly
   this class: pair artefacts by hash, never by name.
3. **No licence is recorded anywhere in the receipt.** `docs/LICENSING.md`
   carries the CC0 determination for the MPFB output and for Faceunits 01, and
   the receipt does not name it. Stage 2 of this lane's brief requires "a
   receipt that names every asset and its licence". Today it names neither the
   licence nor the bytes.

This is a finding and not a fix. It is small, it is inside this lane, and it is
on the MVP path. It needs the orchestrator's word before anything is written,
because `blender_movement_render.py` is the rendering lane's file.

## 7. The defects a coach would see

Taken from `docs/KNOWN_ISSUES.md`, `docs/HANDOFF_RENDERING.md`,
`docs/FAN_AND_RELEASE_PACK.md` and `docs/COACH_FIGURES_PACK_aa3f244.md`, and not
from a new list. Ordered by what a coach meets first. The owner is named,
because most of these are not this lane's.

| # | What she sees | Measured | Owner | Source |
|---|---|---|---|---|
| 1 | The ball is inside her hand at the moment of release, on three of five release phases | 190 vertices 20.27 mm deep on `chest_pass/release`, 120 at 17.76 on `bounce_pass/release`, 78 at 9.55 on `overhead_pass/release`. Every other phase in the library reads 20 vertices or fewer, at 1.65 mm or less | rendering, and it needs a ruling | `FAN_AND_RELEASE_PACK.md` section 3 |
| 2 | The kit is not netball kit. A grey t-shirt and shorts, and no bib | not measured, a judgment | this lane | `HANDOFF_RENDERING.md` defect 2 |
| 3 | The figure stands in a grey room. No cut-out and no contact shadow | not measured, a judgment | this lane | `HANDOFF_RENDERING.md` defect 3 |
| 4 | Her shoulders are narrower than the solve asks | median 43.98 mm, worst 62.01 mm | movement lane, the clavicle normalisation | `KNOWN_ISSUES.md` first entry |
| 5 | One drill is missing from the library | `netball_one_hand_high_pass` cannot pose its `ready` phase. The right index knuckle turns 42.2 degrees about z while the limits are applied to x | rendering | `KNOWN_ISSUES.md` |
| 6 | Her elbows sit too close together with the ball at the chest | 27.3 cm rendered against 38.6 cm in the reference photographs | movement lane | `HANDOFF_RENDERING.md` |
| 7 | The free arm jumps between two frames | on `hooks_outside_hand`, the worst step is now the right upper arm at 11.32 degrees at frame 45. Refer to the caution below the table | movement lane | `KNOWN_ISSUES.md` |
| 8 | Her knees differ on drills that ask for nothing asymmetric | the knee gap runs 4.02 to 6.48 degrees on the shipped build, and 15 of 16 graded below-the-hips checkpoints move between two solutions, by up to 20.65 degrees | movement lane, and it needs a ruling | `KNOWN_ISSUES.md` |
| 9 | Her hand is close to her face on the deflect | open, and the instrument does not exist. The skull sphere reported zero hand vertices inside it, so the instrument failed rather than the pose passing | this lane, a missing instrument | `HANDOFF_RENDERING.md` state |
| 10 | The turntable | never verified since it was written | this lane | `HANDOFF_RENDERING.md` state |

**Which build each row was measured on.** Only row 1 is measured on
`2413f9d`, from that build's own archived receipts. Every other row is quoted
from the document named beside it and carries that document's build, which is
not stated here because this lane did not re-measure it. `docs_number_audit.py`
attributes a number to the nearest build named above it, so it reads all of
these as `2413f9d`. They are not. The phenotype values in section 2 are
configuration and not measurements at all.

**Row 1 is already understood, and it is not a solver defect.** The rendering
lane reported it to the movement lane as a release defect, and then WITHDREW it.
The cause is the two-formula switch in section 4, step 6. `holding` goes False
at the release frame, so the wrist's encoding changes in one frame. The two
encodings agree to 0.000 mm on the source rig, and differ by 19 to 35 mm on this
one, because the ball's radius does not scale with the body. Carrying the grip
one frame forward removes 94 and 87 per cent of the depth on two of the drills.
The cost is that the wrist moves 34 to 49 mm away from the arm the solve graded.
Neither option is free, and no choice is made. The two release stills are HELD
out of the coach pack for this reason.

**Row 1 also touches the movement lane's current work.** The release retiming
Marius ruled on this morning changes where the release frame is. This figure
defect sits on that same frame. The two must be looked at together, and this
entry assumes nothing either way.

**Row 7 carries a caution, because the table under it in `KNOWN_ISSUES.md` is
the record of a fault that closed.** That entry is headed RESOLVED. The table
"What is left above 10 degrees, in full" names `hooks_outside_hand` frame 41 at
19.3 and 18.6 degrees, and the same entry's opening says the worst single-frame
turn on that drill is now 3.50 degrees. The entry also withdraws its own
"largest step left anywhere in the library" claim. **So the library-wide worst
arm step is not stated anywhere on the current build.** That is a missing
number, and this lane needs it for item 5 of the brief. It is the movement
lane's to measure.

## 8. What I checked and did not find

Recorded so that nobody repeats it.

- **`bodyClearanceMm` is read.** `scripts/report_clearance.py`,
  `scripts/docs_number_audit.py` and `scripts/wrist_release_options.py` all read
  it. I was about to report it as an unread instrument, and it is not one.
- **The three release intersections are not new.** I measured them from the
  archived receipts before I found them written up in `FAN_AND_RELEASE_PACK.md`,
  with the mechanism and an option table. The numbers agree exactly. Section 7
  row 1 is a re-derivation, and it is not a finding.
- **The root winding is not a defect.** It was investigated and closed with no
  action on 2026-09-02, and the guard once proposed for it would have been
  harmful.
- **`sourceAssets` appears nowhere in `docs/`.** That is why section 6 is
  offered as new.

## 9. How to reproduce section 7, row 1

    python scripts/report_clearance.py .assets/archives/coach-figures-2413f9d

The archive is outside git. Its combined digest is in that directory's
`PROVENANCE.md`, and it is quoted in section 5.

## 10. The fix to section 6, and what it does not do

`asset_licences.py` has no Blender in it, for the same reason
`render_receipt.py` and `finger_curl.py` have none: this module's tests must
run, and the renderer's own tests skip.

**What it does.** It holds the two asset determinations `docs/LICENSING.md`
makes, each quoted verbatim. `licence_for` returns the licence and the sentence
it came from. `source_asset_records` returns path, sha256 and licence per asset.
`Studio.__init__` calls it as soon as the athlete is built, so an asset with no
determination stops the run before any figure is drawn. The receipt then writes
what was already resolved.

**The evidence.** 22 tests in `tests/test_asset_licences.py`, none of which
skips on this machine. Every guard was proved FAILING under eight mutations, and
each mutation was killed by a named test:

| mutation | killed by |
|---|---|
| drop one selected asset from the table | `test_the_generator_selects_exactly_the_licensed_assets` and five others |
| license every asset instead of refusing | `test_an_asset_outside_both_families_raises` and four others |
| misquote the MPFB determination by one word | `test_both_determinations_are_quoted_verbatim_from_the_document` |
| drop the faceunits pack rule | `test_a_face_target_resolves_by_rule_and_not_by_name` and two others |
| put the old bare-path list back in the receipt | `test_the_receipt_writes_the_licensed_records_and_not_the_raw_assets` |
| write the raw assets while still calling the records | the same test, and ONLY that test |
| move the licence check out of `Studio` | `test_the_licence_check_runs_before_any_figure_is_drawn` |
| hash the path text instead of the bytes | `test_the_hash_follows_the_bytes_and_not_the_name` |

**And it was proved in Blender, not only in the tests.** A unit test proving
that a function raises is not proof that a RUN stops.

- **The good path.** `netball_chest_pass`, phase `ready`, rendered on this
  branch. The receipt names commit `9ea602b` with `treeWasClean` true, and all
  15 source assets carry a path, a 64-character sha256, `CC0`, and the sentence
  the licence is quoted from.
- **The refusal path.** The same render, with `ponytail01` removed from the
  licensed table. Blender exited **9**, the output directory was **empty**, and
  **no receipt was written**. The console named the asset and the rule:
  `no licence is recorded for 'ponytail01.mhclo' ... docs/LICENSING.md requires
  the licence of every newly selected MPFB asset to be reconfirmed before
  publication.` The mutation was asserted present before it was applied, so the
  experiment could not have been a silent no-op, and the file was restored from
  git afterwards with a clean `git status`.

**One guard was too weak and the mutation set found it.** The first version of
the receipt test asserted only that `source_asset_records` is called somewhere
in the module. It PASSED with the old bare-path list back in the receipt,
because the call in `Studio.__init__` satisfied it. The test now reads the value
the receipt assigns to `sourceAssets` out of the syntax and pins it. The sixth
mutation exists to prove the difference: nothing else catches it.

**What it does not do, stated so nobody assumes otherwise.**

1. **It licenses nothing.** It transcribes two determinations and refuses
   everything else. A CC0 label here is the repository's document speaking, and
   a test fails if that document stops saying it.
2. **It does not check that the determination is correct.** That is a legal
   reading of an asset's own licence, and it is not a thing code can do.
3. **`create_athlete` and the table are still two lists.** An AST guard binds
   them, and it is proved failing on an asset added and on an asset removed. The
   one-source-of-truth fix, where the generator reads its asset names from the
   table, is NOT done. It changes the rendering lane's generator, and it is
   Chuck's call.
4. **The reference generator is unchanged.** It already hashes its assets, and
   it records one licence for the whole configuration rather than one per asset.
   Converging the two receipts is a separate question and is not answered here.
5. **The archived receipts keep the old shape.** Nothing rewrites them. The test
   that reads the graded build accepts both shapes for that reason.
6. **`sourceAssets` had exactly one writer and no readers when this changed.**
   That was checked with a search across the repository, not assumed. This is
   the failure class where a producer widens its shape and its readers stay on
   the old one, so the absence of readers is the reason this change is safe, and
   it is recorded here rather than left to be re-derived.
