# Travelling receive, settling and pivot integration

Local implementation, 14 September 2026, MTI-004. Studio build `8c749a42487e31e32a1ebd71f052e2af01d22efaf7edf184bc6cc6aa22493f3b`.

## Review

Open http://127.0.0.1:5397/, choose **Movement source → Braven Tactics**, then **Preview → Moving receive, pivot and pass**. Selection autoplays. Useful moments are 1.4 s (moving catch), 1.8 s (settled feet), 2.2 s (pivot) and 2.8 s (release). Saved setups retain the preview choice, playhead, height, kit and camera; restoring stays paused. The existing Gait and carry preview remains available.

In the local Tactics app, expand **Braven Movement** and choose **Open moving receive and pivot**. This opens an ordinary editable project, with a path, facing keys and actual ball events. The same project builder and footwork functions drive Studio. The correction also applies to ordinary drawn passes; the browser verification includes real Move-circle and Pass-circle gestures.

## Root cause and implementation

Native catch/pass Actions replaced all the locomotion bones, including the legs, while the player continued along Tactics' evaluated path. A planted source pose therefore travelled with the actor. The pre-correction rig measurement reproduced more than 5 mm of support-foot movement in a 1/120-second sample.

`src/core/athleteFootwork.ts` in Tactics now derives foot targets from the existing evaluated actor path. Foot contact phase advances with path distance. Each stance target stays at a fixed point on that path; the other foot swings to its next placement. Stride length follows the route's authored pace and remains constant through instantaneous gait thresholds. The stance reach is bounded relative to athlete height. These are presentation presets, not a measured athlete gait profile.

When the path stops, both feet settle over 180 ms. During a turn, the right support foot stays at the reference placement and the free foot lifts and steps around it. The right side is the existing deterministic preview convention; it does not determine the legal landing foot. The planner also retains the final distance after a drawn run ends, including when another run exists later on the same actor.

`src/engine/athleteFootwork.ts` solves hip/knee rotations and foot orientation after the native pose. It does not translate or scale limb bones. It leaves the torso, arms, fingers and `Ball_Control` untouched; the match-ball evaluator and grip sidecar remain authoritative. Targets enter through `ActorState.athleteFootwork`, so the renderer does not accumulate actor positions or planted-foot state between frames. Only immutable rig reference geometry is cached. Reverse scrubbing samples the same pose again.

The correction fades with the native clip's weight. It does not replace ordinary stationary source poses, airborne techniques, other sports or opted-out plays. Tactics' airborne-role rendering also bypasses it. The authored player path, facing, possession, release/catch timing and existing jump animation are unchanged.

Producer/consumer files:

- Tactics: `src/core/athleteFootwork.ts`, `src/core/evaluate.ts`, `src/core/types.ts`; `src/engine/athleteFootwork.ts`, `tokens.ts`, `skinned.ts`; `src/state/athleteFootworkDemo.ts`, `src/ui/AthleteMotions.tsx`.
- Movement: the Studio preview imports those same functions; its selector, saved setup validation, title and capture filename carry the integration-preview identity.

The model remains revision 7, GLB SHA-256 `ec305d0203331ef77c69eb159db66c086ffbe4345eea6fe5e360b930930f6865`. Native Blender Actions, phenotype, kits, export and contact sidecar are unchanged. This contextual correction is runtime behavior; downloading the GLB alone does not bake a Tactics court path into it.

## Verification

- Tactics: **3,217 tests passed; one optional fixture emitter skipped.** The final athlete build passed TypeScript, Vite and service-worker generation, with the existing bundle-size advisory.
- Actual GLB tests cover support motion at 1, 3 and 6 m/s, a turned path, the pivot at heights 1.60/1.75/1.95 m, unchanged hand/ball positions, unchanged limb lengths and deterministic reverse sampling. Supporting-foot movement/target error stays within the 3–4 mm test tolerances during full-weight contact phases. The original sliding behavior is also measured in the same test. The new support test was observed failing before implementation.
- Domain tests cover stopping after a drawn run, a second later run, stationary and airborne exclusions and sport/library opt-out.
- Studio: **11 unit tests, 11 new footwork browser checks, 44 existing Studio checks and 69 animation-control checks passed**. The new preview was visually inspected on desktop and mobile, including a moving catch and lifted free foot during pivot.
- Tactics: the footwork browser journey checks the real demo button, moving/settling/pivot states, the one match ball, planted support, backwards scrubbing and actual Move/Pass gestures. The ordinary Flat/Bounce/Lob and quick-return journey is rerun alongside it. Receipts live in Tactics' ignored `verification/athlete/footwork/` and `verification/athlete/ordinary-passes.json`; Studio receipts live in `verification/footwork/`, `verification/studio/` and `verification/animation-controls/`.

All **seven footwork browser checks, 14 ordinary-pass checks and five compiled-package checks passed**. The older pass harness initially timed out during its first drag; it now waits for the camera to settle and delivers pointer movement over actual rendered frames. The rerun exercised all three pass types and both players successfully. The compiled checks verify build stamp, real playback, exact model hash, offline reload and no application exceptions.

Compiled Tactics build **`mu17seh9 df62c37-dirty`** runs at http://127.0.0.1:5396/. Its files and receipts are in the external `Netball Athlete/candidates/07-realism/` package. The preceding Tactics runtime was copied to that candidate's `revisions/tactics-before-footwork/` before updating. The model remains revision 7.

The first drawn-run stop test sampled after its source clip had ended; it was corrected to exercise the actual active-clip stop window. The first browser gesture check selected answer buttons incorrectly because the real answers are spans; its selector was corrected, and the real gesture passed. Successful browser runs reported no application exceptions.

Native Blender/gravity/seam suites were not rerun for this runtime-only change. Their revision 7 evidence remains in [REALISM.md](REALISM.md). No new coaching approval is implied.

## Remaining work

This is a bounded foot-placement pass. The native pelvis/torso momentum is still inherited, not dynamically solved from ground forces. Swing targets beyond the leg's reach are clamped without stretching bones; clip fades deliberately transition away from a fully locked foot. Landing-foot choice, toe/heel roll, larger turns, extreme speed/direction changes, cloth collision and arbitrary body proportions need further work. Runtime footwork is not a rules adjudicator. Source stance quality and contextual high/low/one-hand catch selection remain separate work.

Both owned worktrees remain local and uncommitted; no PR, merge or deployment is part of this change.
