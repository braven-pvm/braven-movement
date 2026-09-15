# Revision 7: ball flight and catch response

Local review build, 14 September 2026. Studio build `3d7d59f40796eb206d9094620d49a8c1b3105040965a5bccf3e8c3ce100ed5b4` at http://127.0.0.1:5397/. Runtime GLB SHA-256: `ec305d0203331ef77c69eb159db66c086ffbe4345eea6fe5e360b930930f6865` (17,089,224 bytes). The same GLB and regenerated grip sidecar are imported into the owned Tactics checkout.

## Findings and changes

The earlier [motion audit](MOTION-AUDIT.md) measured some entire pre-contact windows. Those included time when an external feeder had not yet thrown the ball; their average speed and acceleration were not valid flight measurements. The pinned source's release state establishes the actual flight window. On revision 6, ordinary incoming balls travelled horizontally at about 5.7 m/s with vertical acceleration around −5.3 to −6.5 m/s² after retargeting. Jump retiming produced approximately −43.4 and −103.5 m/s² for the incoming jump-catch and double-foot-landing balls. Body jumps themselves were already gravity-corrected.

`../refine_realism.py` now bakes free ball flight in fixed world coordinates, independently of body retargeting and jump time compression. The original source flight duration ends at the revised hand contact. Before the external throw, the ball is hidden and Studio says **Waiting for pass**. Incoming, controlled, released and rebounding states are visible beside the preview. Held-ball poses and source contact/release instants are retained.

The versioned authoring recipe is `../realism.v1.json`. At the 1.75 m Studio reference height, gravity is 9.81 m/s². Dedicated preview throw speeds follow the current Tactics netball settings: chest/bounce 12 m/s, shoulder 17 m/s and overhead 14 m/s. A 4.5 m level target is an illustrative preview setup. The bounce reaches the court at two-thirds of that distance and retains 75% of horizontal and vertical speed, matching Tactics' existing coefficients. Its clip extends from 1.583 to 1.767 seconds to show impact and rebound. New **Floor contact** and **Rebound** phase buttons expose those moments; the camera includes the floor impact.

Five grounded catches receive a small authored response: up to 28 mm of pelvis lowering and 35 mm of hand/ball give, peaking 100 ms after contact and recovering by 380 ms. IK preserves the source foot positions and the orientation of the gripping hands. This is a bounded presentation correction, not a force, muscle or centre-of-mass simulation. The imported source motion and original jobs remain intact and retain their original review status.

Tactics receives the changed body Actions and regenerated contact coordinates. Its `evaluateFrame` still owns the one match ball, free flight and possession; the native preview ball stays hidden on the court. The legacy `braven-athlete-v6` family identifier remains the compatible 70-bone interface; the asset manifest/sidecar revision is **7**. No pass-selection or match-flight runtime logic changed in this pass.

## Editable artifacts and rebuilding

Candidate folder:

`E:\cloud services\OneDrive - About IT Group (Pty) Ltd\Documents\ChatGPT\Braven Movement\Netball Athlete\candidates\07-realism`

It contains the editable master, phenotype source, GLB, manifests, recipe and native verification receipts. The accepted revision 6 remains at the parent `Netball Athlete` root. Rebuild the candidate from that root's master and pinned `movement-library`:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' -b --python-exit-code 9 -P athlete/refine_realism.py -- --input '<baseline>\netball-athlete.blend' --library '<baseline>\movement-library' --output '<candidate>'
.\athlete\Open-Braven-Studio.ps1 -Rebuild -AthleteOutput '<candidate>' -NoBrowser
# In the companion owned Tactics checkout:
node tools/import-athlete.mjs '<candidate>'
npm run build:athlete
```

The Studio launcher records the last successful source paths locally. A subsequent `-Rebuild` without arguments was verified to retain revision 7. Native downloads expose this revision's master and GLB. Studio's joined Receive/pass sequence remains a preview composition; the native general `Receive_pass` Action remains its original demonstration.

## Verification and limits

- **42 realism checks passed:** actual rendered incoming/outgoing gravity, constant horizontal flight, visibility states, contact continuity, bounce floor clearance/rebound, five grounded catch responses and preserved two-hand grip offsets. Measured outgoing acceleration is −9.809 to −9.812 m/s²; incoming samples are −9.69 to −9.813 m/s². Foot displacement from the source stays below 2 mm; the hand/ball relationship stays within 4 mm on the checked two-hand catches.
- **44 Studio and 69 animation-control checks passed**, including autoplay, persistence, revision label, pose editing, carry, frame capture and mobile layout. All **17 clip clocks**, **11 slow-frame playback checks**, **10 jump checks** and **12 technique-ball checks plus eight library checks** passed. Ten workspace/catalog unit tests passed.
- **Native Blender checks ran and passed**, including all 17 Actions, four working IK controls, packed textures, GLB round-trip bones and garment armatures. GLB structure/weights and garment seam checks passed. The native receipt matches the final GLB hash above.
- **Tactics: 3,209 tests passed; one optional fixture-emitter test skipped.** TypeScript/Vite/service-worker build passed, with the existing bundle-size advisory. All **14 ordinary-pass browser checks passed** on revision 7, including Flat/Bounce/Lob drawn through real Pass circles, both rigs, quick return, grip/path continuity and playback. One earlier run timed out during its first mouse gesture while several browser suites ran concurrently; the isolated rerun passed unchanged. The Models-tab label exception discovered by the Studio suite was fixed and the full suite rerun successfully.
- Catch/hand contact, floor bounce, mobile Studio and the rendered Tactics receiving player were visually inspected. Successful browser receipts contain no application exceptions.
- **Four compiled Tactics checks passed** at http://127.0.0.1:5396/: real template playback, exact revision 7 model hash, offline reload after first use and no application exceptions. Build `mu16vbnw df62c37-dirty` is packaged under the candidate folder's `tactics/`, with `Open-Braven-Tactics.ps1` and `tactics-build-receipt.json`. Development remains at port 5395.

Ignored receipts: `verification/realism/`, `verification/realism-regression/`, `verification/studio/`, `verification/animation-controls/` and `verification/motion-audit/revision7.json`; Tactics receipts are in its `verification/athlete/`. `realism/before.json` retains the possession-aware revision 6 measurement. Use `node tests/realism.mjs`, `node tests/studio-browser.mjs`, `node tests/animation-controls.mjs` and the existing motion/playback harnesses to reproduce.

This first realism pass remains local and uncommitted. Contextual catch selection, travelling foot plants, pivots, full-body momentum, cloth collision and athlete-specific timing still need work. Uniform height scaling also scales a baked preview trajectory; the stated gravity and throw-speed measurements apply at the reference height. The Tactics match ball retains world gravity independently of player height. No source technique gains coaching approval through these presentation corrections.
