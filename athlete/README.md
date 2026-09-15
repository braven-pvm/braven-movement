# Braven netball athlete — working prototype

**Maintained internal app:** [Braven Studio](viewer/README.md) now provides a searchable
library, kit browsing, review notes and persistent saved setups around this athlete.
Run `Open-Braven-Studio.ps1` from this source folder for `http://127.0.0.1:5397/`.
The original packaged POC described below remains available separately.

Revision 7 (14 September) is now the local Studio/Tactics review candidate. It corrects independent ball gravity, makes the bounce visible, and adds a small grounded catch response while preserving feet and hand contact. Editable files are under the external output's `candidates/07-realism/`; revision 6 remains the accepted baseline. See [realism changes and measured verification](viewer/REALISM.md). The maintained Studio launcher remembers this candidate on rebuild.

Built on 11 September 2026. One realistic adult female athlete, authored independently of the earlier Movement pipeline. The implementation uses Blender/Python for source authoring and Three.js for interaction; the comparison with Unity, UE5, Character Creator, MHR and other routes is in [the pipeline evaluation](../docs/NETBALL_ATHLETE_PIPELINE.md).

Revision 6 (14 September) corrects the floating jumps. Jump & reach, jump catch/pull-in and double-foot landing use gravity-based flight, with airborne times of 0.424, 0.300 and 0.383 seconds. The general jump now loads before take-off and absorbs after touchdown. The two imported clips retain their source poses and hand/ball relationship on revised timelines. The studio opens on Jump & reach. The prior master and timing are archived under `revisions/04-movement-before-gravity/`.

Studio update 5 (14 September) fixes playback timing. At 1x, the playhead now follows elapsed time even when rendering misses frames. Pause, speed changes and scrubbing synchronise the clock; a hidden tab resumes from its current pose. The demo recording now runs at 1x. The model and authored clip durations remain revision 4.

Revision 4 (14 September) adds twelve existing Braven Movement techniques, their animated ball, wrists and fingers. The geometry and seams accepted in revision 3 are retained. There are now 17 editable Actions and 70 deformation controls, including `Ball_Control`. The original revision 3 model is archived under `revisions/03-seams/` in the delivery.

Revision 3 (14 September) fixes the garment seams. The jersey now has connected shoulder bridges, continuous neckline/armhole cuts, smooth deformation weights and separate editable fabric binding. A turned waistband uses the jersey's weights at the join and covers the tucked shirt and shorts. The accepted light-skinned Caucasian appearance, fitted skirt body and hem height are preserved. The 27.5 cm skirt body now has a 3.5 cm waistband above it. Earlier models are retained under `revisions/01-original/` and `revisions/02-fitted/` in the output folder.

## Try the delivered model

The packaged files are in:

`E:\cloud services\OneDrive - About IT Group (Pty) Ltd\Documents\ChatGPT\Braven Movement\Netball Athlete`

Run `Open-Athlete-Studio.ps1` from that folder, or:

```powershell
python serve.py --root studio --port 5393
```

Open **http://127.0.0.1:5393/**. The packaged studio needs Python to serve local files and a WebGL-capable browser; it does not need Blender, Node, an internet connection or a Tactics checkout. Its Tactics pose adapter is bundled at build time. The PowerShell launcher starts the local server hidden and verifies the served asset hash before opening the browser. `-NoBrowser` starts only the server; `-Port 5394` selects another port.

1. Select a Movement catch or pass, then **Play**. Named phase buttons pause at contact, release, pull-in or follow-through. Turn **Repeat motion** off to play once. Scrub, slow playback and drag to orbit. The original five demonstrations remain under **General movement**.
2. Open **Kit**. Switch skirt/shorts and change team, hem or shorts colours. Height uniformly scales the athlete.
3. Pause at a useful frame and open **Pose**. Choose any of 70 deformation controls, including fingers, skirt panels and ball position, and adjust local rotation/position. Save and reload the pose as JSON. **Bind pose** resets the whole skeleton.
4. Under **Animate → Movement source**, choose **Braven Tactics**. Walk/run/sprint/carry use the actual Tactics `pose` and `applySkinnedPose` functions.

Reduced-motion browser settings start playback paused. The studio's pose JSON is its own editable-pose format, not a Tactics project file. Opening Pose from Tactics mode returns to the authored athlete's last pose. GLB/Blender download buttons return the built master asset; browser colour, height and pose changes are not silently baked into that download.

## Delivered files

| File | Purpose |
| --- | --- |
| `netball-athlete.blend` | Packed editable mesh, materials, skin weights, 70 deformation bones, four native IK targets, 17 Actions and studio lighting. |
| `athlete-source.blend` | Original MPFB human with phenotype shape keys, before flattening the runtime mesh. Use for body-shape development. |
| `netball-athlete.glb` | Portable runtime mesh, textures, rig, weights, animated ball and all 17 clips. Approximately 17.1 MB; 74,347 exported vertices across mesh primitives. |
| `movement-library/` | Pinned Movement source snapshot, twelve full solved jobs, hashes and original checkpoint results. No MHR character mesh is included. |
| `movement-library.json` | Technique phases, source status, exact GLB hash and retarget fit measurements. |
| `manifest.json` | Phenotype inputs, Blender version, source asset declarations/hashes and output hashes. |
| `studio/` | Built browser studio, bundled Tactics adapter, and downloadable model sources. |
| `athlete-in-motion.webm` | Recording of the actual live WebGL model. |
| `*-verification.json`, `verification/` | Numeric results, browser checks, screenshots and a saved edited pose. |
| `source/` | This independent generator, viewer source and instructions, plus the Tactics patch needed to rebuild the adapter. |

The body, hair, eyes, brows, lashes and shoes use selected MakeHuman/MPFB assets whose source headers declare CC0. Jersey, shorts, skirt, lettering and demonstration animation are authored here. See the manifest and linked primary-source licensing information in the evaluation. The rig retains individual fingers. The skirt shares the hips/thighs' skin weights and has 16 additional panel bones for subtle secondary deformation.

## Edit in Blender

Open `netball-athlete.blend` in Blender 4.5 or later. Textures are packed. Select `Netball_Athlete`, enter Pose Mode, choose a bone and rotate it; use the Action Editor to select and edit any of the 17 Actions. The rig is drawn in front of the mesh. `Ball_Control` moves the ball independently; its transform is keyed in the same Actions. The master runs at 60 fps; the original five Actions were retimed to preserve their duration.

For native inverse kinematics, set the rig Object's custom property `IK_hand_l`, `IK_hand_r`, `IK_foot_l` or `IK_foot_r` to **1**, then move the matching `CTRL_hand_l` / `CTRL_foot_l` etc. in Pose Mode. Each drives a two-bone, non-stretching chain. The default **0** keeps the authored FK clips. Place the target at the current hand/ankle before enabling IK to avoid a jump. Finger bones remain independently editable. The native IK constraints/targets are deliberately retained in Blender and omitted from the deformation-only runtime export.

`Kit_Jersey`, `Kit_Shorts` and `Kit_Skirt` are separate weighted meshes. Hide the skirt for shorts; hide it in both viewport and render when rendering the shorts kit. Edit garment vertices/weights/materials directly. The default bib is GS; change or regenerate the lettering for another position. For body proportions, begin with `athlete-source.blend`; refit clothing and check weights after material shape changes. Browser height is uniform scaling, not a new body phenotype.

The five general actions are independently authored examples: Ready, Jog, Defence, Receive_pass and Jump_reach. The twelve new actions use Movement's solved technique data. Neither set is motion capture or coach-approved on this athlete. The skirt follows weighted panel bones; there is no real-time cloth collision solver. Extreme manual poses may need garment corrections. Facial expression rigging, corrective shape keys, production LODs and broad device/performance tuning remain future work.

## Imported Movement techniques

The source is Braven Movement commit `b4f707478ddea3240110f80b5d8e7373a884cb90`. Exporting from a committed snapshot avoids mixing ongoing edits into the library. Each job retains all source frames, normalized limb targets, elbow poles, wrist/palm orientation, finger directions, root travel, airborne height, ball positions and named phases. The athlete is retargeted with its own limb lengths; its mesh and skeleton are retained.

| Technique | Existing source checkpoints |
| --- | --- |
| Two-hand snatch, pull in | Passed |
| Chest pass | Passed |
| Overhead pass | Passed |
| Bounce pass | Passed |
| One-hand high pass | Passed |
| Outside-hand hook catch | Passed |
| Double-foot landing | Passed |
| Chest catch | Needs review |
| Two-hand snatch, straight back | Needs review |
| One-hand snatch and transfer | Needs review |
| Jump catch and pull in | Needs review |
| High deflection | Needs review |

The selector groups the five outstanding source checks separately. Source checkpoint success is not coaching approval of this retarget. Holding wrist targets are preserved numerically, but skin contact, anatomy and coaching form still need review. Different clavicle proportions shift the shoulder-relative ball anchor by up to 18.8 mm on the outside-hand catch; the other techniques remain within 6.2 mm. Bounce pass includes the source's throwing action and initial outgoing trajectory; its short source clip ends before the ball reaches the floor. It does not show a complete court bounce. The final finger segment uses the preceding direction where the source skeleton lacks a fingertip joint.

The gravity correction uses the pelvis as a proxy for body mass and bakes a 9.81 m/s2 downward flight curve into the existing skeleton. It is an animation correction, not a full biomechanical centre-of-mass or contact-force simulation. The imported jumps keep their original jobs unchanged; `sourceTiming` and `sourceFrameMap` in `movement-library.json` record how poses, phase buttons and possession events were retimed. The ball moves with the root correction to maintain the original contact relationships. All keys remain editable in Blender.

## Rebuild the asset

Use the isolated Movement checkout `F:\Repositories\braven-movement-netball-athlete`. `build.py` authors the independent base athlete. `import_movement_library.py` subsequently uses the pinned Movement retarget helpers and solved motion jobs.

Requirements: Blender 4.5 LTS with the MPFB extension and its core asset packs. This build used Blender 4.5.12 and MPFB build 20260722. `build.py` discovers the extension's installed asset directory and fails if a selected source lacks its CC0 header. It has not been tested against arbitrary MPFB versions or modified core asset packs.

```powershell
$athleteOutput = 'E:\cloud services\OneDrive - About IT Group (Pty) Ltd\Documents\ChatGPT\Braven Movement\Netball Athlete'
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' -b --python-exit-code 9 -P athlete\build.py -- --output $athleteOutput --render
python athlete\verify_asset.py --asset "$athleteOutput\netball-athlete.glb" --tactics 'F:\Repositories\braven-tactics-netball-athlete' --report "$athleteOutput\asset-verification.json"
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' -b --python-exit-code 9 -P athlete\verify_blender.py -- --output $athleteOutput
```

`build.py` creates a new scene and writes the named output files. Rebuilding replaces previous exports in that output directory; save artist edits separately. Body phenotype parameters are at the beginning of `main()`. Garment fit is calibrated to this athlete; changing phenotype is an authoring operation requiring fit review.

To re-bake the delivered Movement jobs without running MHR, use the archived base or a fresh base build as input and a separate destination:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' -b --python-exit-code 9 -P athlete\import_movement_library.py -- --input "$athleteOutput\revisions\03-seams\netball-athlete.blend" --library "$athleteOutput\movement-library" --output "$athleteOutput\rebuilt-movement"
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' -b --python-exit-code 9 -P athlete\verify_movement_library.py -- --output "$athleteOutput\rebuilt-movement" --library "$athleteOutput\movement-library"
```

Re-exporting newer source techniques requires Movement's activated `pixi` environment and MHR assets. Run `athlete/export_movement_library.py --source <Movement checkout> --assets <MHR assets directory> --output <new library directory>` through that environment. Directly invoking its Python executable can omit native-library activation. The delivered jobs and snapshot already contain what Blender needs; normal studio use and re-baking do not need the MHR runtime.

Apply the gravity correction after importing the library, or reproduce it from the archived pre-correction master:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' -b --python-exit-code 9 -P athlete\correct_jumps.py -- --input "$athleteOutput\revisions\04-movement-before-gravity\netball-athlete.blend" --output "$athleteOutput\rebuilt-gravity"
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' -b --python-exit-code 9 -P athlete\verify_jumps.py -- --output "$athleteOutput\rebuilt-gravity"
```

Use a separate destination. `correct_jumps.py` rejects an already-corrected input. Its source-frame anchors are calibrated to the delivered Movement snapshot; review new choreography before applying them to a different source revision.

## Build the studio and connect the full Tactics app

The companion isolated Tactics checkout is `F:\Repositories\braven-tactics-netball-athlete`, branch `codex/netball-athlete`. Its small change in `src/engine/skinned.ts` recognises `bravenAthlete: 1`, preserves authored textures/materials, selects the actual skirt mesh, skips duplicate generated clothing/hair, and retargets the panel bones. Unmarked legacy models retain their original path. Per-instance materials are cloned; geometry/textures remain shared.

To build from another Tactics checkout, first apply `source/tactics-authored-athlete.patch` from the packaged delivery, or use the matching branch. The expanded patch is based on Tactics `df62c37`; it includes the full skeleton timeline integration, local build mode and regression tests. Run its import tool against this output directory to populate the model assets before building. It is not applied to either primary checkout or deployed to the live application.

Requirements for rebuilding the viewer: Node 22.12+ (tested on 24.12), npm, and the modified Tactics checkout. From `athlete/viewer`:

```powershell
$env:BRAVEN_TACTICS_PATH = 'F:\Repositories\braven-tactics-netball-athlete'
$env:BRAVEN_ATHLETE_OUTPUT = 'E:\cloud services\OneDrive - About IT Group (Pty) Ltd\Documents\ChatGPT\Braven Movement\Netball Athlete'
npm ci
npm run dev  # http://127.0.0.1:5391/
# Or npm run build: creates dist/ including model downloads.
```

To load this asset into the **full Tactics application**, run from the companion Tactics checkout:

```powershell
node tools/import-athlete.mjs '<Netball Athlete output directory>'
npm run dev:athlete
```

Open **http://127.0.0.1:5395/** and create or open any netball play. The local build automatically uses all 70 rig controls. Normal passes select chest, shoulder, bounce or overhead clips; actual receivers and interceptors use the catch clip. Quick returns blend from the catch into the throw while keeping both contact times. No demo or manually scheduled technique is required. The optional **Netball — new athlete animations** play and all 17 individual clip demos remain available. The adapter hides each athlete's preview ball while the shared evaluator aligns the match ball and drawn trajectories with native contact anchors. Use **Open-Braven-Tactics.ps1** in the delivery for the independent packaged build at **http://127.0.0.1:5396/**. See `TACTICS-LOCAL-BUILD.md` for detailed scope and validation.

## Verification

The standalone asset verifier checks the actual GLB binary: all 21 joints required by the live Tactics source are skin joints, weights sum to one, all three kit meshes are skinned, and each animation has changing channels with finite values and strictly increasing times.

The Blender verifier reopens both native files, checks packed textures and editable phenotype, moves all four IK targets, and reimports the GLB with its rig, skins and clips. These checks actually run Blender; they are not the older opt-in integration suite.

`verify_seams.py` checks connected fabric, closed thickness, the three binding loops, the unchanged skirt hem, tucked overlap and waistband clearance from the jersey at 31 samples across each complete animation. `viewer/tests/seams.mjs` captures front, side, back and raised-arm close views from the actual GLB. Run it with the same environment variables as the browser test. These are garment construction and animation checks; the model does not contain a cloth collision solver.

The Chrome test samples **deformed skinned vertices**, verifies deterministic scrubbing for every clip, changes kit and materials, edits a joint, saves/restores the resulting pose, tests mobile layout, downloads source files, and drives all 14 generated athletes through a real Tactics play. It reports browser errors and saves screenshots. Start both servers first, then from Movement:

```powershell
$env:BRAVEN_TACTICS_PATH = 'F:\Repositories\braven-tactics-netball-athlete'
$env:BRAVEN_ATHLETE_OUTPUT = $athleteOutput
node athlete\viewer\tests\browser.mjs
node athlete\viewer\tests\movement-library.mjs
node athlete\viewer\tests\playback.mjs
node athlete\viewer\tests\jumps.mjs
node athlete\viewer\tests\record.mjs
```

The browser scripts use `puppeteer-core` installed in the Tactics checkout and local Chrome. `CHROME_PATH`, `ATHLETE_URL` and `TACTICS_URL` can override their defaults. Browser screenshots and reports are linked to the exact GLB SHA-256 in the manifest. The final validation summary records passed and skipped legacy coverage separately.
