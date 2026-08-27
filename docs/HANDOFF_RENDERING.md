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
| `spikes/export_manual_page.py`, `spikes/manual_page_template.html` | The manual page. Still draws the older SMPL-X figure. |
| `config/reference_catch.v1.json` | The one authored reference pose, calibrated against a photograph. |
| `scripts/render-reference.ps1`, `scripts/test-blender.ps1` | The runners. |

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

Render the phase stills, three views each.

```bash
"/c/Program Files/Blender Foundation/Blender 4.5/blender.exe" -b --python-exit-code 9 -P blender_movement_render.py -- --job spikes/poc-output/netball_two_hand_snatch_pull_in.job.json --output out
```

Add `--turntable 12` for twelve angles of each phase, `--animate` for the GLB
and the video, `--no-stills` to skip the phase pictures, and
`--phase contact` to do one phase only.

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

## Hard-won gotchas

Ignoring these will cost hours. Each one already did.

1. **`export_apply=True` is not optional.** MPFB hides the fitting helpers and
   the body under the clothes with two mask modifiers, `Hide helpers` and
   `Delete.<garment>`. The glTF exporter ignores modifiers unless asked.
   Without the flag the athlete arrives wearing a skirt of helper geometry to
   the floor, with ladders down her thighs, streaks across her face and her
   chest through her shirt. MakeHuman's base mesh is 19158 vertices of which
   only 13380 are the body.

2. **`blender_mpfb_reference_catch.py` still lacks that flag.** Its own GLB has
   the same defect. It is untouched because it is the validated path with its
   own receipts and tests. Fixing it is the first item in "Known defects".

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
    chase it.

## Do not grow the rasteriser

`spikes/render_figure.py` draws a figure with a depth buffer in numpy. It was
written before this lane used Blender and it is a dead end for anything a coach
sees: seven seconds a frame, no materials, no shadows, and a nude grey body.
Keep it as a fast debug view of the solve. Anything a person looks at goes
through Blender.

The same applies to `spikes/smplx_body.py` and `spikes/smplx_retarget.py`. They
wear an SMPL-X body on the solved pose and they feed the rasteriser and the
current manual page. SMPL-X is in under a **research licence** and needs a
commercial licence from the Max Planck Institute before anything is sold. MPFB
does not. Refer to `LICENCE-RISK.md`. Moving the manual page onto the Blender
path removes that risk, and it is in "Known defects" below.

## Licence

- **MPFB and the generated character:** `docs/LICENSING.md` records the output
  as CC0. Reconfirm the licence of every newly selected MPFB asset before
  publication.
- **SMPL-X:** research licence only. Never commit the model files. Refer to
  `LICENCE-RISK.md`.
- **three.js:** not committed. Fetched on demand.

## Known defects and open work

Ordered by how much they cost.

1. **`blender_mpfb_reference_catch.py` exports without `export_apply=True`.**
   Its GLB has the helper geometry and the unclipped body. Anything consuming
   those files gets it. The fix is one argument, but that module is the
   validated path, so its receipts and `scripts/test-blender.ps1` need checking
   after the change.

2. **The manual page still draws the SMPL-X figure.** `export_manual_page.py`
   uses the rasteriser. Moving it to Blender stills gives it materials, kit and
   shadows, and removes the research licence from the product path.

3. **The kit is not netball kit.** `female_casualsuit02` is a grey t-shirt and
   shorts. A bib in team colours is what a netball manual shows.

4. **The ball is a coral sphere.** It is the right size, 0.11 m radius, and it
   does not look like a netball.

5. **No transparent background or shadow catcher.** A manual page usually wants
   the figure cut out with a contact shadow, not a grey room.

6. **Only one drill has been through the pipeline.** There are eight. The
   batch does not exist.

7. **The viewer plays two animation clips.** Blender exports the athlete and
   the ball separately. The viewer plays both, which is correct, but a reader
   that plays only the first shows the ball standing still.

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

Verified on 2026-08-19, on `claude/repo-onboarding-6c4df5`.

- The pipeline runs end to end on `netball_two_hand_snatch_pull_in`.
- Four phases, three views each, plus a twelve angle turntable.
- An animated GLB of 49 frames at 30 fps, 10.5 MB, and an MP4.
- The exported GLB re-imports into a clean Blender and renders correctly.
- 34 repository tests and 201 spike tests pass.
