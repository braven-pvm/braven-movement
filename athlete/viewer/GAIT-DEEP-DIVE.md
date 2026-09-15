# Jog integration: deeper review, 14 September 2026

Local candidate for Marius's repeated report of broken-looking jogging. The prior
native Jog and forward-knee fixes were insufficient: neither checked continuity
through the complete drawn path, ankle recovery and the orientation of the skin
around the knee.

## Reproduced causes

1. The ordinary Tactics gait uses the compact capture in `figures/clips.json`, not
   the native GLB `Jog` Action. A discrete speed threshold switched between captures
   with different strides and phases. A drawn jog changed the right calf by
   **45.73 degrees in 1/120 second** on walk-to-jog. A drawn run had a **121.37 degree**
   jog-to-run jump. Steady running itself was not the cause of these discontinuities.
2. Moving-catch IK constrained the ankle position and forward knee bend but retained
   roll from an unrelated planted catch. The skin's knee plane differed from the
   geometric bend plane by up to **16.98 degrees** in the regression fixture.
3. Recovering feet stayed level in world space. The relative ankle rotation reached
   **63.86 degrees** from its bind pose. The hard, almost-straight IK reach clamp
   also produced repeated sudden changes in knee flexion.

`verification/athlete/gait-deep/` in the Tactics worktree retains the keyed and drawn
baseline audits, failing regression logs, current results, real UI project and
side/front rendered frame sequences. Maximum angular speed alone did not identify
the fault: steady running also contains fast legitimate knee movement.

## Changes

- Athlete-enabled plays derive continuous gait presentation weights from evaluated
  speed. The coach's path speed, discrete gait label and explicit keyed gait override
  retain their meaning. Existing steady jog and run capture samples are unchanged.
  Every result is an absolute sample; no previous-frame smoothing/cache was added.
- Pose blending retains lateral limb angles, which the previous blend dropped.
- Leg IK now solves a complete anatomical frame from the bind pose and bend plane,
  rather than preserving arbitrary roll from the catch pose.
- A soft extension region removes the hard straight-leg reach singularity.
- Swing shoes follow the shin within a **0.6-radian presentation envelope**. Planted
  support feet retain their flat orientation. This is an animation constraint, not
  a claimed clinical range for every athlete.

The match ball, contact timing, native upper-body clip and fixed bone offsets are
preserved. No model geometry, skin weights, native Action or Blender master changed.
The shared solver is rebuilt into Studio as well as Tactics.

## Verification and delivery

- Tactics: **3,226 tests passed; one optional fixture emitter skipped**. The three
  new actual-GLB regressions failed before implementation and passed afterward.
- Drawn jog maximum joint step across start, cruise and stop: **45.73 -> 9.37 degrees**
  per 1/120 second. Drawn run: **121.37 -> 15.61 degrees**; its steady capture remains
  exactly unchanged. These are fixture measurements, not universal motion bounds.
- Moving-catch fixture: maximum sampled calf step **13.90 -> 6.77 degrees**; swing
  ankle **63.86 -> 34.38 degrees**; knee-plane error **16.98 -> 5.46 degrees**.
- Eight browser checks passed using a real Move gesture, the Jog marker on the
  speed control (rounded to 3.7 m/s), an ordinary Flat pass, full-catch ball alignment,
  anatomical checks and playback. Side and front sequences were visually inspected.
- Three compiled import/playback checks passed using that actual authored Jog play.
- Five compiled build/model/playback/offline checks passed. The first offline run
  timed out waiting for `networkidle0` after three checks had passed; app exceptions
  were empty. The rerun waits for DOM/app readiness and then verifies the model fetch
  with the browser explicitly offline. Both the failed receipt and successful rerun
  are retained; no product change was needed for this test-wait correction.
- Studio: eleven footwork/pivot/height/persistence/browser checks passed.
- Both production builds passed. Native Blender integration was not rerun because
  the asset did not change; it is not counted as a passing check for this update.

Current Tactics: **mu1bosts df62c37-dirty** at
`http://127.0.0.1:5396/?build=mu1bosts`.
Current Studio: **c5ac2f99fae9ff57916cea4d8b20e7d7c525cf94801c108efe5df663492fe94d**
at `http://127.0.0.1:5397/?build=c5ac2f99`.
Asset revision 8 remains
`55c611f1a525c1ec873dfe2aa01970f806c1090c9081973ac14ca1148847a412`.
The previous compiled Tactics package/receipt is preserved at
`Netball Athlete/candidates/08-jog/revisions/tactics-before-gait-dive/`.

This candidate has not yet received Marius's visual acceptance. It fixes the
reproduced transitions and moving-catch leg mechanics; it does not replace the
steady compact jog with the separate native Jog Action or claim a complete
locomotion/cloth/contact system. Full-catch grip checks apply while the native
motion has full weight: `Ball_Control` is not the fallback carrying-hand marker
once the clip has faded out. Everything remains local and uncommitted.
