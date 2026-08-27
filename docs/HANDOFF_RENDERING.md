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

1. **She does not grip the ball. No finger touches it.** The ball floats beside
   a nearly open hand. This is the first thing a coach will see, and it is on
   every manual figure of a held phase.

   Measured with `finger_surface_clearance`, and against the evaluated skin
   mesh, on three phases across two drills:

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

Verified on 2026-08-19, on `claude/handoff-rendering-docs-0c5db3`. That branch
merged `claude/repo-onboarding-6c4df5` into the six commits `main` carried.

- The pipeline runs end to end on `netball_two_hand_snatch_pull_in`.
- Four phases, three views each. The turntable is unchanged and untested since.
- The animated GLB and the MP4 both build. Verified at 5 frames, not at 49.
- Both exported GLB files re-import into a clean Blender and render correctly.
  The body arrives at 10256 vertices with no shape keys.
- The reference generator passes: elbows 106.67 and 114.73 degrees, 30 finger
  bones weighted.
- 55 repository tests and 201 spike tests pass. 17 of the repository tests skip
  without Blender.
