# Jog distance and court contact, 14 September 2026

Marius found the preceding candidate's joints better, but the athlete still appeared to skate: leg turnover did not agree with court travel. This correction targets ordinary jogging and its moving catches in Tactics.

## Current local candidate

- Tactics **mu1cw0rh df62c37-dirty**: http://127.0.0.1:5396/?build=mu1cw0rh
- Studio **7f1e694469c954a021f1ce14937a99ba53ddf8407ccefd9e8132a25e686212df**: http://127.0.0.1:5397/?build=7f1e6944
- Native asset remains revision 8, SHA-256 `55c611f1a525c1ec873dfe2aa01970f806c1090c9081973ac14ca1148847a412`.
- Both implementations remain local and uncommitted in the owned `codex/netball-athlete` worktrees. The preceding compiled package, **mu1bosts**, is preserved in `Netball Athlete/candidates/08-jog/revisions/tactics-before-contact-sync/`.

## Causes and changes

Ordinary jogging used a compact capture stride of **1.7144 m**. A moving catch at 3.78 m/s and athlete height 1.75 m used a different **2.39435 m** stride. Ordinary jogging had no court contact solver, while the catch switched that solver on with a different cycle. This meant about 265 versus 189 steps/min at the same travel speed.

The whole jog now uses one distance-derived cycle for the body capture and foot targets, including its catches and throws. Actual path section speeds determine its stride; a stale overall run speed cannot override the speed selected for every section. Stance targets remain at a fixed court location while the body moves over them. Timeline time and distance are sufficient to reproduce the pose; there is no previous-frame pose state. Tactics continues to own the actor path and match ball.

Two further defects appeared when measuring actual contact geometry:

1. The old captured body height could put a foot target beyond the real leg's reach. Lowering the locomotion base to the rig's reachable support height removed up to 5.4 cm of measured ankle drift. This preparation happens before native action blending so full-weight native hand/ball contact is retained.
2. Some trainer sole vertices inherited shin weights. One sole vertex had 17.5% calf influence, causing 1.77–2.07 cm of visible drift even with a fixed ankle. The shared model loader now clones the footwear geometry and transfers sole calf influence to the matching foot bone, blending back into the original binding up the sock. Toe influence remains editable. **This is a runtime binding correction; the downloadable GLB and Blender master were not rebaked.**

The swing foot lifts clear of the court, and the ankle envelope engages gradually after toe-off. The final settling step also has clearance. A test measuring sole speed close to the floor caught scraping that an ankle-only test missed.

## Verification on this candidate

| Check | Result |
| --- | --- |
| Full Tactics suite | **3,230 passed; one optional fixture emitter skipped** |
| TypeScript, Vite and service-worker build | Passed |
| Actual GLB jog, with/without catch, 480 samples each | Max planted ankle drift under 0.94 mm with catch; effectively zero without |
| Curved jog, actual lowest sole vertices, 1.60 m and 1.95 m athletes | Stance drift below 0.001 mm; sole height within 2.18 mm of court; reverse scrubbing identical |
| Near-floor shoe speed including start/stop | At most 0.044 m/s in the two curved fixtures; the failing version reached 5.59 m/s |
| Real Move gesture, Jog speed control and Flat pass in browser | **10 checks passed**; 1.04 mm maximum support-foot drift, continuous 2.36775 m stride at 3.7 m/s, native catch ball contact preserved |
| Compiled saved-play import and actual playback | **3 checks passed**, exact build mu1cw0rh |
| Compiled template playback, model fingerprint and offline reload | **5 checks passed**, exact build mu1cw0rh; receipt `verification/athlete/package-browser.json` |
| Studio contextual footwork, heights, saving/reload and mobile | **11 checks passed**, build 7f1e6944 |

The source tests cover acceleration/deceleration continuity and preserve the steady fast-running capture. No new Blender integration run was needed or claimed: this change does not re-export the native asset.

Browser artifacts are in the Tactics worktree's `verification/athlete/jog-contact/`: the normal UI-authored `jog-review-project.json`, `browser-after.json`, `compiled-browser.json`, and fixed-camera side/front plain-jog and stopping frames. Earlier failing and final focused measurements are in `verification/athlete/gait-deep/` (`contact-red.log`, `contact-first.log`, `sole-diagnostic.log`, `sole-ground.log`, `clearance-second.log`). The fixed-camera plain jog, front view, stop and moving-catch images were visually inspected.

## Review and limits

Reload the Tactics candidate, open an existing play, and play a drawn path set to Jog at 1×. View from the side: a planted shoe should remain on its court footprint while the body travels over it, then lift and advance. Passing to that player should retain the same leg cycle. The saved browser fixture can also be opened through Settings → Share → Open a file.

This is a bounded contact/cadence correction, awaiting Marius's visual acceptance. Steady fast running retains its previous capture. Continuous contact is selected for jogging paths or explicitly keyed Jog; a path mixing fast-running and slower jogging sections is not comprehensively handled by this whole-path stride policy. Stops still use a short presentation settling step, and full-body momentum, natural foot roll, explicit landing-foot choice, and general motion matching remain future work. Studio incorporates the shared loader/solver in its contextual preview; its standalone native Jog Action has not been retimed by this patch.
