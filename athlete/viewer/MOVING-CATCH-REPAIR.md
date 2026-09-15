# Moving-catch knee repair — 14 September 2026

Marius's recording `20260914-1339-07.7679911.mp4` showed the issue continuing in compiled Tactics `mu1ab8gg`, during a normal moving receive at quarter speed. The preceding standalone Jog correction did **not** fix this reported path. That investigation found an actual ankle problem, but its demo-based verification was too narrow to establish the user's issue was resolved.

## Cause and correction

`src/engine/athleteFootwork.ts` projected the stationary catch clip's knee position onto each moving hip-to-foot line and used that as the IK bend direction. As a travelling foot crossed the source knee, that projection changed sign. The solver consequently chose a backwards knee bend and moved between forward and backward solutions. Keeping bone lengths fixed and hitting the foot targets did not detect this error.

The solver now uses the athlete's anatomical forward direction, projected perpendicular to the hip-to-foot line, to select the forward knee bend. A deterministic vertical fallback covers a degenerate projection. The existing foot targets, fixed limb lengths, pose blending and single authoritative ball remain in place.

Reproduced on an ordinary three-metre-per-second jog into an automatic catch. At play time 2.675 s the old left knee bent backwards; the same frame now bends forwards. Across 234 rendered frames the minimum signed bend changed from **−0.12524** to **+0.00172 square metres**. This is a geometric direction check, not a clinical joint metric. The standalone Jog Action is not involved in this reproduction.

## Verification

- Three new actual-GLB tests **failed before the fix** for backwards knees, at different actor heights/headings/paces. They now pass through the locomotion-to-catch fade, full receive, and fade back to locomotion, with fixed bone offsets, quaternion continuity and unchanged grip position. Signed bend is checked; an unsigned knee angle alone cannot distinguish a backwards knee.
- Full Tactics suite: **3,223 passed, one optional fixture emitter skipped**. Type check and athlete build passed.
- Actual Move/Pass browser gestures: **eight checks passed**, including 362 rendered receiving-leg samples without backwards bends, stable pivot support and single-ball grip. The generated play is saved at Tactics `verification/athlete/footwork/drawn-catch-project.json`.
- Compiled app: **three checks passed** opening that generated play through Settings → Share → Open a file and playing through the receive. This tests a normal play, not the standalone Jog demo.
- Studio shared runtime: **11 footwork browser checks passed**, including pivot, alternate heights, reverse scrub, saved setup and mobile width. Oblique before-and-after rendering was inspected for the reproduced moving catch, alongside the supplied recording's side view.
- Compiled package: **five checks passed** for exact runtime identity, real normal-play playback, asset hash, offline reload and no application exceptions.
- Evidence: Tactics `verification/athlete/receive-knee/{before,after}.json`, matching PNGs and `compiled-browser.json`; Movement `athlete/viewer/verification/jog-video/` contains extracted recording frames and the Studio build log.
- Native Blender/GLB suites were not rerun: the revision 8 model and all Action/mesh data are unchanged in this runtime-only correction. The earlier native Jog repair remains documented separately in `JOG-REPAIR.md`.

## Local delivery

Tactics http://127.0.0.1:5396/?build=mu1an7c1 — **mu1an7c1 df62c37-dirty**. Studio http://127.0.0.1:5397/?build=4b4de6cf — **4b4de6cfc558aa28903606d68434377bd2271ab9342d28cd2d46fe89bd96b8a7**. Model revision 8 hash remains `55c611f1a525c1ec873dfe2aa01970f806c1090c9081973ac14ca1148847a412`.

The compiled package remains under `Netball Athlete/candidates/08-jog/tactics/`. Its preceding runtime and receipt are preserved at `revisions/tactics-before-knee-fix/`. Rebuild Studio from the owned Movement checkout and Tactics from the owned Tactics checkout. Both worktrees remain local/uncommitted. Full-body momentum, toe/heel articulation and explicit landing-foot policy remain separate work.
