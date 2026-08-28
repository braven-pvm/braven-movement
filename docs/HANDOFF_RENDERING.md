# Handover — the rendering and modelling lane

Paste the block below into a fresh session. Everything after it is reference.

---

## The prompt

You own **the athlete and the picture** for Braven Movement. Another lane owns
the movement, the anatomy and the solver. The two meet at one JSON file and
never at any other point.

Your job is to make what a coach looks at: manual pages, figures, video, and an
interactive model. The movement arrives already solved and already graded
against a coaches manual. You do not solve it, and you do not change it.

**Repository:** `F:\Repositories\braven-movement`
**Read first:** `docs/ARCHITECTURE.md`, then this document fully.

Start by proving the pipeline still runs end to end on one drill. Refer to
"Running things" below. Then read "Known defects" and pick from it.

---

## What this lane owns

| File | What it does |
|---|---|
| `blender_mpfb_reference_catch.py` | Creates the MPFB athlete, poses one reference catch, renders and exports. The posing helpers live here and everything else imports them. |
| `blender_movement_render.py` | Poses every phase or every frame of a solved movement and renders it. Turntable, animation, GLB and video. |
| `blender_glb_render.py` | Renders an inspected GLB job. |
| `spikes/movement_viewer.html` | Interactive three.js viewer for the animated GLB. |
| `spikes/render_figure.py` | A software rasteriser in numpy. **Debug view only.** Refer to "Do not grow the rasteriser". |
| `spikes/export_manual_page.py`, `spikes/manual_page_template.html` | The manual page. Assembles the manual's words and the Blender stills. It solves, poses and renders nothing. |
| `spikes/export_figure_check.py` | One figure, full size, through the rasteriser. **Debug view only**, and the last place SMPL-X reaches a page. |
| `config/reference_catch.v1.json` | The one authored reference pose, calibrated against a photograph. |
| `scripts/render-reference.ps1`, `scripts/test-blender.ps1` | The runners. |
| `finger_curl.py` | The geometry of a closing finger, and the flexion-axis rule, with **no Blender in it**. Extracted so a test can call it. Refer to known defect 1. |
| `render_receipt.py` | What a render run may claim about itself. `PASS` only when something was produced. |
| `scripts/video_sync_sheet.py` | Front and side frames of the real athlete video, paired at matched wall clock. Refer to "The video instruments". |
| `scripts/keypoint_overlay.py` | The movement lane's keypoints drawn over the video they came from. It draws and it does not solve. |
| `scripts/compare_lift_against_view.py` | A lifted 3D joint angle against the same angle read from one camera. Reports the PROJECTION FLOOR, which is the disagreement that is geometry. |

## What this lane must not touch

Everything in `spikes/` that solves or grades a movement. Named plainly:
`movement_engine.py`, `contact_solve.py`, `possession_solve.py`,
`motion_track.py`, `movement_definition.py`, `segment_measures.py`,
`grip.py`, `ball_track.py`, `technique.py`, and every file under
`spikes/movements/`.

If a figure looks wrong, measure it and report it. Do not correct it by moving
a target in the renderer. A pose that is wrong is a finding for the movement
lane, and correcting it here hides it. Two defects are open right now and both
belong to that lane. Refer to "What the other lane is fixing".

## The boundary

`spikes/export_blender_job.py` writes one job file per movement. That file is
the entire interface. It carries no absolute geometry except the ball, because
the MPFB athlete is not the size or shape of the athlete the engine solves on,
and a world coordinate measured on one body lands in the wrong place on the
other.

```
schemaVersion, movementId, skill, sport
anatomyLimitsDegrees   forearmRoll, wristBend, fingerJointBend,
                       fingerBaseDeviation
knuckleLimitsDegrees   index, middle, ring, pinky, thumb. Refer to the note
                       below before consuming it
views                  front, quarter, side
                       resolutionPx, locationM, targetM, lensMm, sensorWidthMm
framesPerSecond, frameStep
phases[]               the coaching phases, for stills
frames[]               every Nth frame, for animation. Empty unless the job
                       was exported with --every=N
```

Each phase and each frame carries:

```
frame                          the source frame number
name                           phase name. Frames have none
arms.{l,r}.direction           unit vector, shoulder to wrist, world
arms.{l,r}.reachFraction       0 to 1 of that arm's own length
arms.{l,r}.pole                unit vector, the direction the elbow leaves
                               the shoulder to wrist line
hands.{l,r}.fingerDirection    unit vector, wrist to middle knuckle
hands.{l,r}.palmNormal         fingerDirection crossed with the knuckle line
stance.ankleFromPelvisInLegs   {l,r} ankle offset from the pelvis, in leg
                               lengths
ball.radiusM                   absolute. A netball is a netball
ball.fromShouldersInArms       ball centre from the shoulder midpoint, in arm
                               lengths
ball.holding                   whether she has it
grip.{l,r}.outward             present only when holding. Unit vector from the
                               ball centre to that wrist
grip.{l,r}.wristFromSurfaceInArms   how far outside the ball surface the wrist
                               sits, in arm lengths
```

### knuckleLimitsDegrees, and the rule behind it

**The rule, which is general.** A POSE crosses this boundary as geometry,
because a rotation only means something against the rest pose it was measured
in and the two rigs do not share one. A RANGE OF MOTION crosses as a rotation
about the anatomical axis, because it is a fact about the joint rather than a
configuration.

The first version of this field broke that rule: it exported a range of motion
as visible bend, which is comparable to nothing a consumer computes. It never
shipped to a consumer.

**What is carried.** Per digit, including the thumb, in degrees:

```
flexion    {min, max}   about the knuckle's own curl axis
deviation  {min, max}   about the knuckle's own deviation axis, side to side
visibleBendAtFlexionLimit   informational only, refer below
```

**Resolve into the joint's frame first.** These bound rotations about the
joint's own axes. A consumer reading them as palm-relative or world angles is
wrong in a way nothing catches.

**A scalar bend is not this quantity.** Rotating a finger in the plane that
points it at the ball is not rotation about the flexion axis. Off that axis
the single rotation mixes flexion with deviation, so bounding the mixture by
the flexion licence permits a deviation the joint does not have. It is the
mirror of clipping: the same number, over-permitting instead of over-clipping.

The rendering lane measured their bend axis at 8 to 16 degrees off flexion on
the four fingers. First-order arithmetic, so treat it as an indication and
measure directly: spending the full flexion licence through a 16.2 degree
tilted axis costs the pinky about 25 degrees of deviation on top of the 28 it
already carries at rest, which is past its deviation limit while passing a
scalar flexion check.

The rule that follows: decompose the knuckle rotation in the hand's own frame,
bound the flexion component by `flexion` and the deviation component by
`deviation`.

**The thumb is carried, and it is the reason not to skip this.** Its licence
is materially tighter than a finger's — flexion −11.5 to 57.3 against a
finger's −44.7 to 90, deviation ±28.6 against ±45.8. A consumer ceiling of 80
degrees is above the model's 57.3, so before this field the thumb was not
merely unbounded, it was over-permitted.

**Per digit, and the reason is extension, not flexion.** Flexion maximum is
90.0 on all four fingers, so a per-digit flexion maximum varies for no
anatomical reason. The digits differ in extension: the pinky reaches −57.3
where the others reach −44.7.

**`visibleBendAtFlexionLimit` is informational and is not a ceiling.** It is
the visible angle between wrist-to-knuckle and knuckle-to-phalanx when the
curl axis is at its limit and the other two are at zero. It exists so nobody
clips a legal pose. Two worked cautions, because both are mistakes waiting to
happen:

- **It is not the rest bend plus the rotation limit.** The index rests at 18.5
  with a rotation limit of 90 and reaches 90.0 of visible bend, not 108.5.
  These are measured by driving the parameter, never computed by addition, and
  a test fails if anyone replaces the measurement with the sum.
- **A visible reading may legally exceed it.** The index shows 96.4 of VISIBLE
  bend at contact on the one-handed drills. That is not an over-rotated joint:
  it is about 78 of curl-axis rotation, with the other two knuckle axes
  contributing the rest. Quoting the two quantities against each other is the
  error; 96.4 is visible bend and 90.0 is a rotation limit.

**Never the word metacarpal.** Neither rig has one. MPFB has 30 finger bones
and none of them is a metacarpal, and MHR's equivalent segment is
wrist-to-knuckle. Rest bends differ per digit AND per rig, which is why a
consumer must use its own:

| digit | MHR rest bend | MPFB rest bend | difference |
|---|---|---|---|
| index | 18.5 | 13.80 | 4.7 |
| middle | 8.0 | 19.39 | 11.4 |
| ring | 1.2 | 16.78 | 15.6 |
| pinky | 14.6 | 18.34 | 3.7 |

**`anatomyLimitsDegrees.fingerBaseDeviation` is unchanged** at 40.0 and still
means deviation. It is a calibration of one authored pose against one
photograph, so prefer the model-derived `deviation` above, which is per digit
and licenses ±45.8 on a finger.

**Reaching and holding are different, and the difference is the whole
possession model.** Before contact the arm decides where the hand goes, so use
`arms`. After contact the ball decides, so place the ball first from
`ball.fromShouldersInArms`, then put each wrist on it with `grip`. Deriving a
grip from shoulder directions closed the hands from 19.0 cm apart to 12.1 on a
narrower pair of shoulders, and put both hands in front of the ball instead of
either side of it.

The hand frame is built with the same formula `hand_basis` uses in
`blender_mpfb_reference_catch.py`. Keep it that way. Both sides then agree
without anyone guessing a sign convention.

## Running things

Blender 4.5 LTS with MPFB, at
`C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`. Verified with
4.5.12 LTS and MPFB build 20260722.

Write a job for one movement. Add `--every=2` if you want animation frames.

```bash
cd spikes && "$USERPROFILE/.pixi/bin/pixi.exe" run python export_blender_job.py netball_two_hand_snatch_pull_in --every=2
```

Write a job for every drill the possession model is ready for.

```bash
cd spikes && "$USERPROFILE/.pixi/bin/pixi.exe" run python export_blender_job.py --all --every=2
```

Render the phase stills, three views each.

```bash
"/c/Program Files/Blender Foundation/Blender 4.5/blender.exe" -b --python-exit-code 9 -P blender_movement_render.py -- --job spikes/poc-output/netball_two_hand_snatch_pull_in.job.json --output out
```

`--job` repeats. Give it every job and one session renders the lot, which
matters because building the athlete costs about two minutes and a phase view
costs about seventeen seconds. Eight drills are 33 phases and 99 views, so
about half an hour.

Add `--turntable 12` for twelve angles of each phase, `--animate` for the GLB
and the video, `--no-stills` to skip the phase pictures, and
`--phase contact` to do one phase only. `--animate` takes one job.

Build the manual page from those stills. It reads the render receipts and the
job files and renders nothing itself.

```bash
cd spikes && "$USERPROFILE/.pixi/bin/pixi.exe" run python export_manual_page.py --renders ../out/manual
```

Serve the viewer. Pass `?glb=<path>` for a movement other than the default.

```bash
cd spikes/poc-output && python -m http.server 8731
```

The reference generator, unchanged.

```bash
pwsh scripts/render-reference.ps1 -Output out
```

Tests. The Blender ones need Blender; the rest do not.

```bash
python -m unittest discover -s tests
```

## The video instruments

Vision point 2 is the real player. Marius filmed a sample session on
2026-08-28: two drill sets, each from a front and a side camera about 90
degrees apart. The material is at `.assets/video-samples/session-1.0/`, four
mp4 files, read only.

**The movement lane owns the extraction**: the sync, the 2D keypoints and the
two-view 3D lift. This lane owns every picture a person looks at. The keypoint
file is the boundary, and its shape is settled in
`spikes/VIDEO_KEYPOINT_SCHEMA.md`.

### Facts about the material, measured and not assumed

- The front files carry **rotation metadata of -90**. Their containers say
  1024x576 and their decoded frames are 576x1024. Check the decoded pixels,
  never the container.
- The side files are **variable rate**, but barely: intervals run 33.22 to
  33.42 ms with five distinct values and NO dropped frames.
- **The side camera's clock runs 0.0398 percent faster than the front's.** Four
  derivations agree. Over a 29 s clip that is 11 ms, one third of a frame, so
  drift is ignorable at this length and is NOT ignorable over a ten minute
  shoot, where the same ratio is 240 ms.
- **There is no clap.** The audio route failed honestly. The first shared event
  is her first ball catch, about 9.25 s on the front and 8.25 s on the side.
- The sample is a **self-fed toss and catch** and matches none of the eight
  drills.
- `front 0.1` degrades from **25.700 s**: sharpness is 87 percent of baseline
  there with the inter-frame motion tripled, 39 percent at 25.900, and the
  frame goes dark at 26.267. Treat 25.7 as its usable end. The other three
  files have no bad tail.

### The two offset conventions, and how they map

They agree on this material and carry OPPOSITE SIGNS in their own definitions,
which is exactly where a consumer trips.

    video_sync_sheet   --offset                    side_time = front_time + offset
    keypoint file      offsetSecondsToReference    add it to a time in THIS file
                                                   to reach the reference clock

    For the non-reference view, offsetSecondsToReference = -(--offset).
    This material: --offset -1.0 and offsetSecondsToReference +1.0 both put
    the front at 9.25 s and the side at 8.25 s.

Neither is wrong and either alone is unambiguous. `keypoint_overlay.py`
asserts the direction against the file's own worked example on load, so a sign
error stops rather than draws.

### The projection floor: a 3D angle and a camera's angle are not one quantity

Measured on 2026-08-28 with `scripts/compare_lift_against_view.py`, over 730
frames of the left arm.

A camera cannot see the axis it looks along. The side camera reads the elbow
angle PROJECTED into its own plane, and that differs from the true 3D angle
even when the 3D is perfect. Take the movement lane's lifted arm, compute the
angle in 3D, then drop `across` and compute it again, which is exactly what a
flawless side camera would read:

    median 4.6 degrees, p90 15.2, worst 55.8

and it grows with how much of the arm lies along the axis the side camera
cannot see, which is the signature it must have:

| the arm's share along `across` | median difference |
|---|---|
| 0.17 to 0.30 | 2.1 degrees |
| 0.30 to 0.42 | 3.7 |
| 0.42 to 0.49 | 5.4 |
| 0.49 to 0.61 | 6.4 |
| 0.62 to 0.98 | 10.6 |

**So any comparison of a 3D solve against an angle read from one camera carries
about 5 degrees of built-in disagreement that is geometry and not a defect.**
On this material a lift-versus-side elbow comparison measured 12.8 degrees
median, of which the floor above is roughly a third. Quote the floor beside any
such number, or a real agreement reads as an error.

The same warning applies to the engine: comparing a solved 3D pose against a
coach's video by eye compares a 3D angle with a projected one.

### A reprojection check on this lift would measure nothing

The lift is not a triangulation. The front view supplies `across`, the side
supplies `ahead`, and each camera's pixels pass through to its own axis, so
reprojecting the 3D into either camera returns the 2D it came from, to
rounding, BY CONSTRUCTION. It would look like a clean verification and would
verify that addition is reversible. A reprojection check is only evidence when
the 3D was solved jointly from both views.

### What these instruments refuse to do

- The sheet **prints the time each frame truly carries**, never the time asked
  for. `ffmpeg -ss` serves the first frame at or after the request, which is up
  to a full frame late and always late, and always late is a bias that reads as
  a sync error.
- The sheet **stamps NOT FOOTAGE** on a frame that is smeared or dark, against
  that clip's own median. Quote the reference with any such percentage: the
  same handling frame reads 26 percent against the clip's settled baseline and
  21 against the median of a sheet's own samples.
- The overlay **refuses to invent a skeleton**. Edges come from the keypoint
  file. `--assume-topology` lets a person override, and the picture is then
  stamped as guessed.
- The overlay **prints what produced its landmarks**, read from the file. A
  viewer cannot tell a real solve from a placeholder by looking at a skeleton.

## Hard-won gotchas

Ignoring these will cost hours. Each one already did.

1. **`export_apply=True` is not optional.** MPFB hides the fitting helpers and
   the body under the clothes with two mask modifiers, `Hide helpers` and
   `Delete.<garment>`. The glTF exporter ignores modifiers unless asked.
   Without the flag the athlete arrives wearing a skirt of helper geometry to
   the floor, with ladders down her thighs, streaks across her face and her
   chest through her shirt. MakeHuman's base mesh is 19158 vertices of which
   only 13380 are the body.

2. **Both exporters set that flag now.** `blender_mpfb_reference_catch.py`
   gained it in `8818015`, together with the shape key bake and the opaque
   skin. A new glTF export needs all three parts. Refer to gotchas 1, 3
   and 4.

3. **Bake the shape keys before export.** `export_apply` disables shape key
   export, so they must be baked or the body reverts to the base MakeHuman
   shape. Baking is wanted anyway: 38 morph targets survive in three.js and
   break most other readers, and baking cut the file from 19.6 MB to 11.0.

4. **Set the skin opaque, never clipped.** Its texture alpha is a second way
   the helpers were hidden. With the modifiers applied it has nothing left to
   hide and only dithers, in angular patches over the legs, arms and face.
   Clipping it instead punches holes through her legs, because the alpha is not
   a clean binary mask. Hair, lashes and brows keep their blending; they are
   cut-out cards.

5. **Verify by re-importing the exported file into a clean Blender and
   rendering it.** Do not trust one viewer. The three.js viewer in this
   repository renders a broken file correctly, so every measurement taken there
   said the file was fine while it was not. The re-import test needs neither a
   browser nor this repository's own viewer.

6. **Blender fits the sensor to the longer side of the image.** These renders
   are taller than they are wide, so 36 mm covers the height. An 85 mm lens at
   3.2 m saw 1.35 m of a 1.75 m athlete and cut her off at the thigh. 50 mm at
   3.2 m sees 2.3 m.

7. **A page that is not visible gets no animation frames.** `requestAnimation`
   never fires, so the render loop never runs and the canvas reads back black
   whether the scene is right or wrong. `window.__viewer.render()` in
   `movement_viewer.html` forces one frame so it can be measured.

8. **three.js is not committed** and must not be, because it is not ours to
   ship. Four `curl` lines are in the comment at the top of
   `movement_viewer.html`. The `lib/` layout must mirror three's own
   directories, because `GLTFLoader` imports its siblings by relative path and
   a flat folder gives a 404 with no message.

9. **Do not use `--factory-startup`** with the MPFB generator. It disables the
   installed extension preferences. MPFB is loaded from Blender's user
   extension directory.

10. **The video render takes about ten minutes.** Use a real background
    mechanism. A shell `&` inside a call that returns immediately gets the
    process killed, which cost two rebuilds.

11. **An artifact page cannot carry the GLB.** It is about 10.5 MB, and base64
    inflates it past the 16 MB ceiling. Serve it over HTTP instead.

12. **An `Icosphere` of 42 vertices appears when you re-import a GLB.** It is
    not in the exported file, which contains seven meshes and none of them is
    it. It is an artefact of the import and reaches nothing downstream. Do not
    chase it. It does sit a metre below the floor, so leave it out of any
    bounding box you frame a camera from.

13. **Do not pass the eyes to `set_alpha`.** The eye mesh is named
    `high-poly` and it carries a transparent cornea over the iris. Opaque
    paints the sclera across the whole eye and she arrives with two blank
    white discs and no pupil. Pass the body and the kit only.

14. **`spikes/mhr-assets/` is gitignored and is 4.5 GB.** A new worktree has
    no copy, and the first command that loads the character fails with
    `Error reading FBX file`. Link it, rather than downloading it again.

    ```bash
    New-Item -ItemType Junction -Path "<new-worktree>\spikes\mhr-assets" -Target "<existing-worktree>\spikes\mhr-assets"
    ```

    A recursive `grep` or `du` over `spikes/` then walks 4.5 GB and stalls.
    Use `git grep`, or scope the search.

15. **This lane and the movement lane break each other without a git
    conflict.** `blender_movement_render.py` imports fourteen helpers from
    `blender_mpfb_reference_catch.py`. When a signature changes on one branch
    and the caller stays on another, no file collides, the merge is clean and
    Blender fails at load. `tests/test_blender_sources.py` now compares both
    sides with the AST and needs no Blender.

16. **A quiet log is not evidence that nothing is running.** Blender's stdout
    buffers through a file redirect, so a long render can be nine minutes into
    real work with an empty log and an empty output directory. Neither says
    the run failed. They say there is no evidence either way, and the evidence
    is in the process table.

    ```bash
    tasklist | grep -i blender
    ```

    A process with hundreds of seconds of CPU behind it is working. Judge a
    render by its artifacts appearing and by the process still being alive,
    never by the log going quiet.

    **The trap that follows.** Reading the quiet as a failure and starting the
    run again gives two Blender processes writing one output directory and one
    log. Whatever comes out of that cannot be trusted, and it looks like a
    result. If a run seems stuck, count the processes first. If two are
    running, stop both and start exactly one, rather than reasoning about
    which output belongs to which.

17. **The poser's bend axis is not the joint's flexion axis, and a joint limit
    cannot be applied to it directly.** `pose_articulated_hand` rotates each
    finger in whatever plane points it at the ball:

    ```
    bend = toward_ball - base * toward_ball.dot(base)
    ```

    The rotation axis is `base` crossed with `bend`, chosen by where the ball
    sits and not by the knuckle. Measured against each joint's own flexion
    axis, found by rotating each local axis a little and keeping the one that
    curls the fingertip toward the palm:

    | digit | contact | pull_in | flexion axis |
    |---|---|---|---|
    | index | 10.1 | 9.2 | -X |
    | middle | 8.3 | 10.9 | -X |
    | ring | 10.3 | 8.3 | -X |
    | pinky | 1.3 | 16.2 | -X |
    | thumb | 46.7 | 60.7 | -Z |

    Both hands agree within 0.3 degrees, so it is geometry and not noise, and
    the tilt changes with the pose: the pinky is 1.3 degrees off axis at
    contact and 16.2 at pull in.

    So a rotation here spends BOTH budgets. To first order it costs
    `theta * cos(tilt)` of flexion and `theta * sin(tilt)` of deviation.
    Spending a 90 degree flexion licence through this axis adds about 25
    degrees of deviation on the pinky, on top of the 28 it already carries at
    rest, which is past the 40 degree limit while the other three fingers stay
    inside it. Bounding one scalar by one limit passes that silently.

    Anything that consumes a per axis joint limit must decompose the rotation
    into flexion and deviation and bound each by its own number. Do not clip
    the visible angle between segments either: that is a third quantity again,
    and the solve legally reaches 96.4 degrees of visible bend on the index in
    the one handed drills.

18. **One instrument is never enough, and a green check is not evidence.**
    Every defect this lane shipped or nearly shipped on 2026-08-27 was
    invisible to the check that should have caught it and obvious to a second
    one that fails differently:

    | the defect | what said "fine" | what caught it |
    |---|---|---|
    | fingers never reached the ball | the render looked plausible | per digit clearance |
    | the ball through her face | every finger at +7 to +9 mm, receipt PASS | the whole-mesh count |
    | every drill playing drill one's motion | posed bones read "identical" | the animation curve counts, 533 against 1063 |
    | fingers inside the ball | the picture, the penetration was behind the ball | the clearance report |

    So the receipt carries two tables, `surfaceClearanceMm` per digit and
    `bodyClearanceMm` for the whole athlete, and neither replaces the other.
    Add a third when a third question appears; do not replace one with a
    "better" single number.

    **Silence is not a pass.** An instrument reporting zero because it cannot
    reach the thing is worse than no instrument. A skull sphere taken from the
    head bone reported zero hand vertices inside the head on a figure where the
    hand is visibly across her face. The number was never delivered, and it
    should not have been. Anything that reads a receipt must separate
    "measured and clean" from "not measured", and say which.

    **A comment is not evidence either.** The grip solve landed fingers inside
    the ball directly beneath a comment reading "land on the near side of
    contact, never inside it" — correct intent, opposite behaviour. Anyone
    checking intent against comment would have passed it. Only a reading of the
    OUTPUT caught it.

19. **Report a stoppage when you stop, not in the summary.** Anything that
    makes you kill a build goes to the coordinator at the time. Milestones can
    be batched; stoppages cannot, because the other lanes are planning around
    a build you have just abandoned.

## Do not grow the rasteriser

`spikes/render_figure.py` draws a figure with a depth buffer in numpy. It was
written before this lane used Blender and it is a dead end for anything a coach
sees: seven seconds a frame, no materials, no shadows, and a nude grey body.
Keep it as a fast debug view of the solve. Anything a person looks at goes
through Blender.

The same applies to `spikes/smplx_body.py` and `spikes/smplx_retarget.py`. They
wear an SMPL-X body on the solved pose. SMPL-X is under a **research licence**
and needs a commercial licence from the Max Planck Institute before anything is
sold. MPFB does not. Refer to `LICENCE-RISK.md`.

The manual page is off that path now. SMPL-X reaches exactly three files:
`smplx_body.py`, `smplx_retarget.py` and `export_figure_check.py`, and every
one of them is a debug view. Nothing a coach or a customer sees imports them.
Keep it that way: if a page a person reads needs a figure, render it in
Blender.

## Licence

- **MPFB and the generated character:** `docs/LICENSING.md` records the output
  as CC0. Reconfirm the licence of every newly selected MPFB asset before
  publication.
- **SMPL-X:** research licence only. Never commit the model files. Refer to
  `LICENCE-RISK.md`.
- **three.js:** not committed. Fetched on demand.

## Known defects and open work

Ordered by how much they cost.

1. **CLOSED. She gripped nothing. The knuckle never flexed.** Kept in full
   because the reasoning is the lane's most useful record, and because
   `scripts/report_clearance.py` refers to this number.

   **State on 2026-08-27, measured from `out/coach-stills2`:** 180 digits over
   eight drills. 170 close on the ball, and every one of those falls from
   knuckle to tip. The ten that do not are the free hand fault below, not this
   defect. The text that follows is history. Do not read it as current.

   The defect, as it read before the fix. Measured with
   `finger_surface_clearance`, and against the evaluated skin mesh, on three
   phases across two drills:

   | Drill and phase | Nearest finger bone | Nearest skin | Vertices inside |
   |---|---|---|---|
   | two_hand_snatch_pull_in, contact | 32.9 mm | +8.8 mm | 0 |
   | two_hand_snatch_pull_in, pull_in | 27.4 mm | +6.2 mm | 0 |
   | double_foot_landing, land | 32.8 mm | +8.2 mm | 0 |

   The renderer places the wrists exactly where the job asks: 14.8 cm from the
   ball centre against 14.8 cm asked for, symmetric, 3.8 cm outside an 11 cm
   surface. It achieves the palm normal to within 0.5 degrees. So the renderer
   is doing what it is told.

   **The knuckle never flexed. That is the defect, and it is this lane's.**
   `curved_directions` built its cumulative angles as `(0.0, first, first +
   second)`, so the first bone of every chain took zero rotation. Only the
   middle and distal joints bent, 8 and 12 degrees. A grip flexes the knuckle
   hardest, and this one did not flex it at all.

   The symptom is a profile that runs the wrong way. Clearance in mm along
   each finger, two hand snatch at contact, before the fix:

   | digit | knuckle | mid | distal | tip |
   |---|---|---|---|---|
   | thumb | +32.9 | +36.2 | +44.0 | +51.2 |
   | index | +46.4 | +57.5 | +67.1 | +76.2 |
   | middle | +46.7 | +60.5 | +72.2 | +81.8 |
   | ring | +45.5 | +56.9 | +66.4 | +74.8 |
   | pinky | +41.3 | +48.9 | +53.9 | +58.3 |

   A grip falls from knuckle to tip, about 40 down to 7 on the solved
   athlete. This climbs. The fingers were not short of the ball. They pointed
   away from it.

   **Two retractions, and both were the same mistake.** A summary number
   stood in for the thing itself.

   1. "The fingers go through the ball." Read off a picture, never measured.
      Zero vertices of any mesh are inside the ball on any phase.
   2. "Curl moves the clearance by 0.00 mm." Read off `worst`, the minimum
      over five digits. That minimum sits on the **thumb's base knuckle**,
      which flexion rotates about and therefore cannot move. It read a flat
      zero while every fingertip moved about 10 mm per unit of curl scale
      underneath it. The index tip runs 86.0 mm at curl 0, 76.2 at curl 1 and
      65.1 at curl 2.

   `finger_surface_clearance` reports per segment now and never a bare
   minimum, because the instrument fooled its own author twice. Read the
   shape.

   **The arm and hand lengths, for the record.** A unit mismatch was proposed
   and does not hold: MPFB's arm is 485.47 mm and its wrist to middle
   fingertip is 181.91 mm, a ratio of 0.3747 against MHR's 0.2897. MPFB's
   hand is proportionally longer, so it would over-reach, not fall short.

   **What was tried before the knuckle was found, so nobody repeats it.**
   Two levers, measured per digit at contact:

   | aim | thumb | index | middle | ring | pinky | base deviation |
   |---|---|---|---|---|---|---|
   | 0.04, as authored | +32.9 | +46.4 | +46.7 | +45.5 | +41.3 | 5 to 16 |
   | 1.00 | −36.9 | +35.9 | +35.0 | +30.8 | +26.8 | 38 to 39 |
   | 3.00 | −48.5 | +9.3 | +4.6 | +3.1 | +8.0 | 59 |

   - **Curl does nothing.** It rotates each bone about the knuckle above it,
     and that knuckle is the part of the finger nearest the ball. Taking every
     joint from 12 degrees to 24, hard against the 25 degree limit, moves the
     clearance by 0.00 mm. It still moves it by 0.00 mm with the wrist placed
     inside the ball.
   - **Aim runs out of anatomy.** `fingerBaseDeviation` allows 40 degrees. At
     that limit the nearest finger is still 27 mm short. The fingers only
     arrive at aim 3.0, half again over the limit.
   - **Solving one aim for the whole hand is worse.** The thumb leans three
     times as fast, reaches the ball alone, and the search stops with the other
     four untouched at 41 to 47 mm. A thumb on the ball and four fingers
     splayed off it reads worse than the gap does.

   **This belongs to the movement lane.** The gap is
   `grip.{l,r}.wristFromSurfaceInArms`, which the job carries at 0.078 to
   0.082. Sweeping it while holding everything else fixed:

   | wristFromSurfaceInArms | wrist from surface | nearest finger |
   |---|---|---|
   | 0.082, as exported | 39.7 mm | +34.6 mm |
   | 0.040 | 19.4 mm | +15.2 mm |
   | 0.020 | 9.7 mm | +6.2 mm |
   | 0.000 | 0.0 mm | −2.8 mm |

   About **0.02** is where the hand meets the ball. Nothing in the renderer
   needs to change once the job says that.

   **A previous version of this document said the fingers go through the ball.
   That was wrong, and it was wrong because it was read off a picture and never
   measured.** What looks like a fingertip emerging from the top of the ball is
   the far hand behind the ball, correctly occluded. Zero vertices of any mesh
   are inside the ball on any phase measured. The receipt now carries
   `hands.{l,r}.surfaceClearanceMm` so nobody has to judge this by eye again.

   The two palm normals point in opposite senses relative to the ball, 13.8
   and 166.2 degrees. **That is correct and is not a defect.** `hand_basis`
   uses `finger` crossed with `index - pinky`, and the lateral axis mirrors
   between hands, so the sign flips by design. The comment there says so. Do
   not "fix" it.

2. **The kit is not netball kit.** `female_casualsuit02` is a grey t-shirt and
   shorts. A bib in team colours is what a netball manual shows.

3. **No transparent background or shadow catcher.** A manual page usually wants
   the figure cut out with a contact shadow, not a grey room. The manual page
   shows the studio render as it is, so this is now visible on every figure.

4. **The viewer plays two animation clips.** Blender exports the athlete and
   the ball separately. The viewer plays both, which is correct, but a reader
   that plays only the first shows the ball standing still.

5. **`delete_helper_geometry` in `blender_movement_render.py` is dead.** It
   deleted the helper vertices by hand before `export_apply` existed. Nothing
   calls it, and its docstring still reads as live guidance. `HELPER_GROUPS`
   is unused with it.

6. **`--animate` takes one job.** The GLB export bakes the shape keys away and
   sets the materials opaque, so a second job in the same session would export
   an athlete already baked. The stills batch has no such limit. Making the
   animation batch would mean rebuilding the athlete, or undoing the bake.

### Closed

- **`blender_mpfb_reference_catch.py` exported without `export_apply=True`.**
  Fixed. Its GLB carried the helper geometry: 21833 body vertices and 22.7 MB
  against 10256 and 12.3 MB now. The 48 shape keys are baked first, because
  `export_apply` disables shape key export.
- **The ball was a coral sphere.** Fixed. `blender_movement_render.py` now
  calls `create_panelled_netball`, which the reference generator already had.

## What the other lane is fixing

Do not work around these. They are being fixed at the source.

- **The elbows sit 27.3 cm apart against 38.6 cm in the reference
  photographs.** A point target on the elbow cannot hold an upper arm up. This
  also blocks a wider grip: opening the grip past 90 degrees currently closes
  the elbows further.
- **`netball_hooks_outside_hand` exceeds a joint limit** on 1 of its 98 frames,
  worst 0.715 degrees. Inside the 5 degree clinical threshold, and still a
  regression.

The plantarflexed foot is **fixed**. Every drill now holds 21.0 to 21.9 degrees
against a rest of 21.0, and the lowest point of any foot is 2.1 cm above the
floor. `blender_movement_render.py` still restores the foot's world matrix
after aiming the leg, which was hiding that defect. That is now belt and
braces rather than a correction, and it can stay.

## State

Measured on 2026-08-27, on `lane/rendering`, which carries `main` at `84fd600`.

**Verified, each by measurement and not by a passing run.**

- All eight drills render in ONE Blender session: 33 phases, 99 images, 8
  receipts, every one PASS. The athlete is built once.
- **The grip closes.** 170 digits of 180 on the ball across eight drills, tips
  0 to 8 mm from the surface, every one falling from knuckle to tip. This
  morning the same fingers were 26 to 35 mm short and CLIMBING. The 10 that do
  not close are two hands on two drills, both named under the pose faults
  below, and both belong to the job and not to the renderer.
- **Animation batching**, proven on two instruments that fail differently.
  Curve counts equal at 533 and 533 with no orphans, where the defect showed
  as 533 against 1063. Bone paths 53.3 mm apart, so the two files carry
  different movements. Frame counts equal, so the timebase leak is closed.
- The manual page assembles all eight: 33 figures, 642 KB, 7 of 8 quoting the
  coaches manual. Checked in a browser at 1265 px and 375 px, both themes.
- The reference generator is unchanged by the knuckle work: elbows 106.67 and
  114.73 degrees, 30 finger bones weighted, and its receipt diffed against the
  pre-fix one to 2.265e-06, which is 0.0004 mm of fingertip travel.
- The suite runs 63 tests and passes. **17 of the 63 skip**: they are the
  Blender integration set, and they run only when
  `BRAVEN_RUN_BLENDER_INTEGRATION=1`. So 46 tests execute by default. Report
  the suite that way. "63 pass" reads as 63 executed, and 17 of them did not.
- This lane added **eight guards**. One of the eight, the clearance profile
  guard, was rewritten once when the instrument it guards changed shape. Every
  guard was verified FAILING with its fix reverted; a guard that has never
  failed has proven nothing.
- **Defect 1 has no direct guard, and nothing in the suite blocks its return.**
  The eight guards cover the seven other defects. The knuckle flexion fix is
  held only by the clearance profile, which is an instrument in a receipt and
  not a test. A guard that asserts on the source text would pass on a file that
  computes the wrong angle, so it would be a guard in name only. The honest one
  calls `curved_directions` and reads the angles, and that needs the function
  lifted out of the Blender module so it imports without `bpy`. That extraction
  is follow-up work, agreed with the reviewer, and it is not in this branch.

**Not verified, and do not report otherwise.**

- The turntable. Unchanged and untouched since it was written.
- The hand against the head on `deflect_high` ready. The defect is visible and
  real. My skull sphere, taken from the head bone's length, reported zero hand
  vertices inside it, so the INSTRUMENT failed and no number was delivered. A
  zero from an instrument that cannot reach the face is worse than no zero.

**Open pose faults, measured and handed to the movement lane.**

Measured from `out/coach-stills2`, the 2026-08-27 evening build, on all eight
drills. **One fault survives.**

| Phase | Vertices inside | Deepest |
|---|---|---|
| `hooks_outside_hand contact` | 469 | 37.1 mm |

The other twelve phases that report anything read 1 to 21 vertices at 0.0 to
1.8 mm. That is contact, not intersection: the render treats the ball as rigid
and a real netball yields several millimetres under a catch. The gap between
the survivor and that group is 35 mm and 448 vertices, which is in the data and
not a threshold anyone chose.

Three faults from the morning table are GONE. `deflect_high control`, which put
the ball through her face at 406 vertices, now reads 4 vertices at 0.4 mm. Both
RELEASE faults are gone, and no release phase reports anything, so the morning
reading that pointed at ball trajectory at release no longer has evidence
behind it. **What closed them is not isolated.** The two builds differ by the
engine work merged into main today AND by this lane's grip fixes, and nobody
ran the one against the other. Do not credit either until somebody does.

**The survivor is one fault seen by both instruments, and it is the FREE hand.**
On `hooks_outside_hand contact` the per digit table reads the left hand thumb
pointing away, +78 mm at the knuckle to +99 at the tip, with the ring and pinky
tips 17 and 35 mm INSIDE the ball. The arm target sweeps a 182 mm hand through
the ball, and the fingers then solve against a surface their palm is already
behind. The renderer places the hand where the job asks. Fixing this by moving
the hand in the renderer would hide it, so three images are held behind a
placeholder instead.

One further hand is judged and should not be. On
`one_hand_snatch_to_other_hand contact` the left hand reads all five digits 101
to 134 mm short. The job carries a grip for the receiving hand at a phase where
that hand has not reached the ball. That is a job question for the movement
lane, not a renderer defect.

The 10 digits that do not close divide between exactly these two hands.
`one_hand_snatch_to_other_hand` contributes 5 short.
`hooks_outside_hand` contributes 2 short, 1 pointing away and 2 inside. No
third hand is flagged on any drill.

**Known limits of the 2026-08-27 batch.**

Its 66 hands carry no usable grip measurement. The render began before the
per segment clearance profile existed, so those receipts hold the older single
number per digit, which is a minimum sitting on the base knuckle. It says
nothing about whether a finger closed. `scripts/report_clearance.py` names
them unreadable rather than guessing. That batch proves pipeline mechanics and
nothing about hands.
