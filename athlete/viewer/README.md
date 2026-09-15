# Braven Studio

The maintained local app for browsing athlete models, kits and animations, saving review setups and showcasing Movement output. First internal version: 14 September 2026. It extends the working Three.js viewer and bundles the compatible Tactics pose adapter.

Latest local candidate: Studio **7f1e6944**, companion Tactics **mu1cw0rh**. Jogging now
shares one distance cycle through ordinary movement and catches, with fixed court
contacts and corrected runtime shoe binding. The native revision 8 asset is unchanged.
See [causes, checks and limits](JOG-CONTACT-SYNC.md); [the preceding review](GAIT-DEEP-DIVE.md)
records the earlier knee/ankle and gait-transition corrections.

## Open the app

From the owned Movement checkout:

```powershell
.\athlete\Open-Braven-Studio.ps1
```

Stable address: **http://127.0.0.1:5397/**. The launcher serves the compiled `dist/` app in a hidden local process and checks its build identity. Running it again reuses the matching server. It does not require an open terminal. After restarting the computer, run the launcher again. Python is required to serve the package. Use `-NoBrowser` to start without opening a browser, or `-Port` if the default port is occupied; another port has separate browser storage.

To rebuild after source edits:

```powershell
.\athlete\Open-Braven-Studio.ps1 -Rebuild
```

The launcher accepts `-AthleteOutput` and `-TacticsPath`, or the existing `BRAVEN_ATHLETE_OUTPUT` and `BRAVEN_TACTICS_PATH` environment variables. Its current-machine defaults point to the accepted athlete output and the companion owned Tactics worktree. A rebuild needs Node >=22.12, the viewer dependencies, the exported model package and compatible Tactics source. Once built, `dist/` contains the application, assets and source downloads; the browser does not need Blender or a running Tactics server.

The original revision 6 POC package remains in the external `Netball Athlete/studio/` folder. Its source was archived as `revisions/studio-before-app/viewer-source-20260914-125713.zip` before the UI changed. The maintained app now uses the **revision 8 Jog correction** in `Netball Athlete/candidates/08-jog/`, retaining revision 7's realism work and preserving that earlier candidate. The launcher remembers the last successful `-AthleteOutput` and `-TacticsPath` in ignored `.local/build-inputs.json`, so rebuilding without arguments retains this candidate. Explicit arguments or environment variables override the saved paths.

## What the team can do

- **Animations:** search 17 movements, filter by passing/catching/footwork/defence, select to autoplay or scrub, step one frame, jump to named phases, change speed and inspect the skeleton or mesh. Space plays/pauses and left/right arrows step when focus is outside a control. Passing/receiving techniques include a ball; Tactics Carry position places a ball in the hands. Receive and pass is a Studio sequence assembled from the native catch and chest-pass clips; its source download retains the original revision 6 demonstration.
- **Kits:** switch the fitted skirt/undershorts or shorts, change three kit colours, restore Braven colours and change uniform height. Garment geometry and body proportions remain editable in Blender. The current jersey still carries GS lettering.
- **Models:** inspect the available adult female athlete, source status, rig information and model fingerprint; download the runtime GLB, native master or body source.
- **Review:** distinguish source-check status from coaching approval and keep notes against each animation. None of the current retargeted techniques is marked coach-approved.
- **Pose:** pause and edit joints, including fingers and garment bones. Import/export standalone pose files, or keep a complete pose inside a saved setup.
- **Saved:** name a setup containing movement/time, kit/colours/height, camera, inspection settings, pose and notes. Reopen after reload, remove with Undo, or export/import a workspace. Imports preserve existing saved setups and refuse mismatched model assets or invalid transforms.
- **Capture:** download a PNG of the rendered athlete at the current pose.

## Persistence and scope

Saved setups and note drafts use browser local storage, scoped to the exact model hash. A later model revision has its own workspace rather than overwriting earlier reviews. Corrupt data is reported and a recovery copy is retained when storage is writable. Storage/quota failures appear as errors; they are not reported as successful saves. Export JSON for backup or to use the workspace in another browser with the matching asset.

This is **local browser persistence**, not team synchronization. Clearing browser/site data removes local work. Shared hosting, sign-in/access decisions and shared reviews belong to the next phase. There is no login or team backend in this build. The catalog currently has one model, two garment choices and 17 clips; it does not imply that more bodies or sports have been built.

## Development and verification

From `athlete/viewer/`, set both source environment variables, then:

```powershell
npm ci
npm test
npm run dev
# Development URL: http://127.0.0.1:5391/
npm run build
node tests/studio-browser.mjs
# Browser harness expects the compiled app at http://127.0.0.1:5397/.
```

`tests/studio-browser.mjs` uses the companion Tactics checkout's `puppeteer-core` and local Chrome. Override `BRAVEN_TACTICS_PATH`, `CHROME_PATH` or `STUDIO_URL` where needed. It drives actual library, playback, kit, save/import and mobile controls and checks the real rig. Receipts and images are under ignored `verification/studio/`.

Current build: `7f1e694469c954a021f1ce14937a99ba53ddf8407ccefd9e8132a25e686212df`. The [contact/cadence correction](JOG-CONTACT-SYNC.md) addresses skating through ordinary jogging and catches. The [moving-catch repair](MOVING-CATCH-REPAIR.md) records the earlier backwards-knee fix. The earlier [Jog repair](JOG-REPAIR.md) changed only the authored Action. **Braven Tactics → Moving receive, pivot and pass** demonstrates contextual footwork using an actual Tactics project; see [footwork implementation and checks](FOOTWORK.md). The [realism report](REALISM.md) records revision 7's independent ball flight, bounce and catch response. The earlier [motion audit](MOTION-AUDIT.md) records autoplay, ball presence and playback speeds.

Verification:

| Check | Result |
| --- | --- |
| Catalog, workspace validation, recovery and model-version isolation | 10 unit tests passed |
| Autoplay, ball presentation, carry contact and gait cadence | 69 focused browser checks passed |
| Every library clip at 1× | All 17 measured 1.000×; full durations in the motion audit |
| Native Movement ball geometry and controls | All 12 clips and eight associated controls checks passed |
| Compiled app journeys | 44 checks passed; no application exceptions |
| Existing slow-frame playback regression | 11 checks passed; measured 1.000x, 0.500x and 2.000x at approximately 8 rendered frames/second |
| Existing exported-rig jump regression | 10 checks passed; three corrected jumps retain gravity and floor contact |
| Production build and launcher | Passed; launcher reused the same build on a second invocation |
| Visual inspection | Desktop, kit, saved-pose, mobile and jump screenshots inspected |

Detailed current receipts: `verification/studio/browser.json`, `verification/animation-controls/checks.json`, `verification/motion-audit/audit.json`, `verification/regression/playback-verification.json`, `verification/regression/jump-browser-verification.json`, `verification/regression/movement-browser-verification.json` and `dist/studio-build.json`. The current package's GLB hash was independently checked against the accepted asset. The build retains a non-failing bundle-size advisory (approximately 785 KB minified JavaScript, 217 KB gzipped); device-wide performance/LOD work remains separate.

No Blender geometry was regenerated in this UI change. Native Blender checks and the full Tactics suite were not rerun; their earlier evidence is in [the delivery validation](../VALIDATION.md). The two new model-isolation/recovery tests were observed failing before correction, then passed. The initial catalog/workspace test run failed because the new modules did not exist; do not describe that initial import failure as a behavioral regression.

The browser suite also reproduced a late-Tactics-cycle pose-save failure before the fix: the four-second gait cycle could leave a saved time outside the shorter native clip. Entering Pose now samples a valid native clip time before capturing the bones. That regression passes in the final 44-check run.

## Code map

| File | Responsibility |
| --- | --- |
| `src/main.js` | Existing renderer, animation clock, native/Tactics rig controls and setup capture/restore |
| `src/preview-motion.js` | Studio catch/pass sequence, private carry-ball hand contact and gait pace presets |
| `src/catalog.js` | Available models/kits and metadata for the actual loaded clips |
| `src/workspace.js` | Versioned, asset-bound validation and persistence |
| `src/studio.js` | Library, review, save/import/export, capture and keyboard interactions |
| `index.html`, `src/style.css` | Application structure, responsive layout and visual design |
| `vite.config.mjs` | Tactics build adapter, local asset serving/copy and generated build identity |
| `../Open-Braven-Studio.ps1` | Build/start/reopen the stable local application |

Ongoing scope and future hosting work are tracked in the [shared lane backlog](../../docs/lanes/movement-tactics/BACKLOG.md).
