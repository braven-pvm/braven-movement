# Delivery validation — revision 6, 14 September 2026

GLB SHA-256: `32956794e77f6663035b57d0e364fbba70a67e64713725b97fa667faa7b2ba13`

Native master SHA-256: `4cd588fcf7e4668dd73cc6d6c7aa17b67738251bfa80c4564ec04606a47be96c`

Twelve techniques were exported from Braven Movement commit `b4f707478ddea3240110f80b5d8e7373a884cb90` and retargeted onto the accepted revision 3 athlete. The original five clips remain. A skinned ball shares the same editable skeleton and Actions. The source snapshot and every solved job are retained with hashes under `movement-library/`; the previous athlete is archived under `revisions/03-seams/`.

## Gravity correction — revision 6

The old general jump used a sine lift and left the feet airborne for almost one second at 22 cm clearance. The imported jump catch used keyed foot heights that stayed airborne for about 1.6 seconds at only 11 cm clearance. These were authored timing defects after the preview clock had been fixed.

The three revised clips bake ballistic pelvis trajectories at 9.81 m/s2. The pelvis is an animation proxy for body mass, not a biomechanical COM solve. Jump & reach now loads before take-off and absorbs at touchdown. Imported jump poses and ball-relative contact are retained, with shorter airborne timelines and grounded feet during preparation/recovery. Original source timing and the source-to-new-frame mapping remain in the metadata. Revision 4 is archived under `revisions/04-movement-before-gravity/`.

| Clip | Corrected flight time | Native fitted downward acceleration |
| --- | --- | --- |
| Jump & reach | 0.424 s | 9.81 m/s2 |
| Jump catch & pull in | 0.300 s | 9.81 m/s2 |
| Double-foot landing | 0.383 s | 9.81 m/s2 |

Nine native gravity checks and ten exported-rig browser checks passed. Browser measurements on the sampled GLB fit 9.80-9.90 m/s2, with ankle penetration below 0.2 mm. Screenshots cover take-off, apex, touchdown and absorption in `verification/jumps/`; reports are `jump-verification.json` and `jump-browser-verification.json`. The test failed against the prior jump before correction.

## Playback clock correction — retained from studio update 5

The earlier viewer capped each frame's elapsed time at 80 ms. Separate Chrome measurements at the displayed 1x advanced only 3.6 animation seconds in five wall seconds. The fix retains elapsed time during slow rendering and resets the clock on visibility transitions, preventing hidden-tab time from entering playback. Input events synchronise pause and speed changes. The demo recording was regenerated at 1x.

The new browser regression reproduced the failure before the fix. Against the rebuilt packaged studio, all 11 playback checks passed. With 120 ms rendering stalls (about 8.3 rendered frames/second), the measured rates were 1.000x, 0.500x and 2.000x. Pause, scrub, resume and simulated hidden/visible transitions passed. `playback-verification.json` identifies the exact script hash: `87f18d6588d61b6be943a22e146ed5513c3bf52ca1249adced70cd6a72253eb7`.

All 11 playback checks were rerun with revision 6 and passed. The clock preserves playback speed under load; it does not increase rendering frame rate.

## Passed in this revision

- **Asset inspection:** 70 deformation controls, all 21 joints required by Tactics, 74,347 vertices, normalized weights and 17 finite, changing clips. GLB size is 17,070,564 bytes.
- **Native Blender:** 14 checks passed. Both native sources reopened, phenotype shape keys and packed textures retained, all four native IK targets drove their limbs, and the GLB reimported with every bone, Action and garment armature modifier.
- **Movement baking:** 75 checks passed across all 1,180 source frames, using the revised frame mapping for the two retimed imports. Job hashes and Action provenance match. Baked ball positions are finite and animated; holding wrists retain their normalized targets within 0.001 mm. Sampled finger segments retain the imported source directions within one degree. This measures retarget fidelity, not skin contact or coaching quality.
- **Packaged studio / Chrome:** 53 integration checks passed. All 17 clips deform real skinned vertices and scrub deterministically. Kit switching, recolouring, manual pose editing, JSON save/load, downloads and mobile horizontal fit passed. No application JavaScript errors were observed.
- **Movement browser checks:** all twelve clips move both ball and hand geometry. Ball centres follow their controls, scrubbing is deterministic, and the final frame holds correctly. Eight additional checks passed for review grouping, phase selection, single-play/replay, ball visibility and restoring an edited ball pose after switching clips.
- **Full Tactics board:** all 14 players load the authored GLB and move through the real play timeline. Per-athlete preview balls are hidden so the board retains its own ball.
- **Seam regression:** 33 checks passed across 527 animation samples. Connected fabric, closed binding and thickness, unchanged hem and tucked waist overlap are preserved. Maximum inner-waistband distance from the jersey is 0.501 mm. These are construction and deformation checks, not a cloth collision simulation.
- **Visual review:** reviewed technique contact/release/landing frames and close front, side and back garment views, including overhead and crouched poses. Screenshots are under `verification/movement-library/` and `verification/seams-*.png`.
- **Tactics adapter regression (revision 4):** all four authored-athlete tests and `npx tsc -b` passed then. The adapter is unchanged and those checks were not rerun for revision 6; the full browser board test above was rerun.
- **Studio production build:** passed, with a non-failing Vite chunk-size advisory (669 KB uncompressed JavaScript). The adapter and model downloads are bundled for local use without a development server.
- **Recording:** regenerated at 1x from the actual WebGL model playing all three corrected jump/landing clips and chest pass.

## Source checks and limits

Seven source techniques pass their existing checkpoints: bounce pass, chest pass, double-foot landing, outside-hand hook catch, one-hand high pass, overhead pass and two-hand snatch/pull-in. Five source techniques still need review: high deflection, jump catch/pull-in, one-hand snatch/transfer, chest catch and two-hand snatch/straight-back. The studio groups them separately. None is coach-approved on this athlete.

Different clavicle proportions shift the shoulder-relative ball anchor by up to 18.8 mm for the outside-hand catch; all other techniques stay within 6.2 mm. Source finger directions are transferred onto this athlete's fingers, but fingertip shape and skin contact require visual/coach review. The source bounce-pass clip ends before the ball reaches the floor. Source phase labels and actual possession-event frames are both retained; they are not always the same frame.

The local Tactics integration now enables native Actions for every normal netball play and aligns its single match ball and drawn trajectories with the actual release/catch anchors. The native GLB and Blender geometry remain revision 6. The latest Tactics integration passed 3,209 tests (one optional fixture emitter skipped) and the local bundle build. Its new ordinary-pass browser checks draw Flat, Bounce and Lob passes through the court controls, verify both players' native rigs and hand contacts, a quick catch-to-pass transition, trajectory endpoints and playback. The earlier 32 browser checks cover all 17 demos and the full 14-player board. The compiled package has separate playback, model-hash and offline-reload checks. See `TACTICS-LOCAL-BUILD.md` and `verification/tactics/` for receipts and limitations. The skirt is driven by bones. Extreme poses, facial animation, cloth collision and production LOD/performance work remain outside this prototype.

## Historical coverage, not rerun

The original delivery's Movement host suite passed 321 tests with 28 skipped; its Tactics suite passed 3,186 with one optional fixture test skipped. Those whole suites were not rerun for this animation import. The optional broader legacy `spikes/` suite previously stopped without a completion verdict and is not counted as passing. The explicit Blender and browser checks listed above actually ran against this revision.

The work remains local on `codex/netball-athlete` in isolated Movement and Tactics worktrees. Primary checkouts were preserved; no merge or deployment was performed. See `source/athlete/README.md` in the delivery for editing, rebuilding and integration commands. Numeric verification reports carry the exact GLB hash above.
