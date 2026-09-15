# Studio motion audit — 14 September 2026

Build: `2241f9bbe3d64d1fdff7c1f95dba2e112e3c1fbfa8c43235bd9fafe1468c8b2d`.
Model: revision 6, SHA-256 `32956794e77f6663035b57d0e364fbba70a67e64713725b97fa667faa7b2ba13`.

## Changes delivered locally

- Selecting a library card, animation dropdown entry or Tactics gait starts playback. An explicit selection also plays when reduced motion is preferred. Initial load, restoring a saved setup, scrubbing and phase/frame selection remain paused. The chosen playback rate is retained.
- All twelve imported Movement clips retain their original animated ball. The old `Receive_pass` general clip was only an arm-reach loop with a zero-scaled ball. Studio now assembles its demonstration from `netball_two_hand_snatch_pull_in` and `netball_chest_pass`, preserving the 3.033-second duration and blending the overlapping 0.167 seconds. Body, fingers, kit and ball tracks are joined together. This is a Studio sequence; the downloadable GLB and Blender master remain the original revision 6 sources, including the original general demonstration.
- The private Tactics preview clone shows a held ball when Carry position is enabled. A two-link solve uses the skin's actual arm lengths to put both palms on the ball while retaining wrist orientation and bone lengths. It runs after the Tactics gait pose, without changing the Tactics court or its match-ball ownership.
- Ready, Jog, Defence and the unloaded Jump/reach demonstration remain ball-free. The actual jump-catch and double-foot landing techniques include their authored ball.
- Unloaded saved poses can retain the native ball's all-zero hidden scale. Collapsed body-joint scales and partially collapsed ball scales are still rejected.

## Every library clip's clock

Measured at 1× against elapsed browser frame timestamps for at least 0.85 seconds per clip, including wraparound. All 17 measured **1.000×** to three decimal places. Slow-frame regression separately measured 1.000×, 0.500× and 2.000× at approximately 8.3 rendered frames per second. Rendering delays do not stretch the animation's clock.

| Animation | Full duration (s) | Ball |
| --- | ---: | --- |
| Ready stance | 3.033 | Unloaded |
| Jog | 1.033 | Unloaded |
| Defensive stance | 3.033 | Unloaded |
| Jump and reach | 2.000 | Unloaded |
| Receive and pass | 3.033 | Studio joined sequence |
| Bounce pass | 1.583 | Native |
| Chest pass | 1.583 | Native |
| One-hand high pass | 1.583 | Native |
| Overhead pass | 1.583 | Native |
| Chest catch | 1.617 | Native |
| Two-hand snatch, pull in | 1.617 | Native |
| Two-hand snatch, straight back | 1.617 | Native |
| One-hand snatch and transfer | 1.617 | Native |
| Outside-hand hook catch | 1.617 | Native |
| Jump catch and pull in | 1.233 | Native |
| Double-foot landing | 1.350 | Native |
| High deflection | 1.450 | Native |

These are complete clip durations, including preparation, contact/release and recovery. A correct clock does not establish that every phase is athletically realistic. No blanket multiplier was applied to the imported techniques.

## Tactics preview cadence defect and correction

Previously every gait used `time * 2.4` metres. The Tactics pose engine measures stride phase from distance, with a longer stride for a sprint. Feeding every gait the same distance per second therefore made sprint cadence slower than walking.

The preview now supplies separate showcase paces. At the adapter's reference height of 1.75 m:

| Gait | Preview pace (m/s) | Measured full strides in 4 s | Steps per minute |
| --- | ---: | ---: | ---: |
| Ready | 0 | 0 | 0 |
| Walk | 1.4875 | 4 | 120 |
| Run | 3.9375 | 6 | 180 |
| Sprint | 6.65 | 8 | 240 |

These presets complete whole strides within the existing four-second preview, avoiding a phase jump at repeat. They use the current Tactics stride factors (0.85, 1.5, 1.9 × height); actual knee pulses and loop continuity are tested against the imported engine. The displayed pace accounts for uniform athlete scaling. These are illustrative presets, not athlete-specific measured capacities. Real Tactics plays continue using their own evaluated travel distance and timing.

## Evidence for the next realism pass

**Follow-up:** [Revision 7](REALISM.md) separates the external feeder's holding period from true flight. The pre-contact averages below are historical whole-window observations, not free-flight speed/gravity measurements. Use the possession-aware follow-up for the corrected diagnosis and implementation.

The remaining floaty appearance needs work on the ball's trajectory, possession/contact transitions and body response. A global playback-rate change cannot resolve those relationships.

Observed on the final skinned model at 1.75 m:

- The four dedicated throws show approximately 5.8–6.4 m/s displacement-over-time after release and vertical acceleration around −9.4 to −9.5 m/s² over the sampled window. Their outgoing motion is already broadly gravity-shaped. They show only about 0.317 seconds after release; the bounce clip ends before the floor impact can be seen.
- Several catching clips move the ball only about 0.93–1.51 m/s over the sampled pre-contact window. Their vertical acceleration is upward over that window (about +1.6 to +2.8 m/s²). That is evidence to investigate the incoming trajectory and retargeting, not a renderer-clock defect.
- Jump-catch and landing have almost stationary pre-contact samples. Contact metadata does not by itself establish whether each window is flight, an externally held target or possession. Inspect the pinned source's holding/flight states before diagnosing those as gravity failures.
- The existing corrected body jumps remain ballistic: roughly −9.80, −9.90 and −9.80 m/s² for general jump, jump catch and double-foot landing, respectively.

Next work should compare the same source technique and contact instants in Studio and a real Tactics pass. Establish incoming/free-flight/held/released states, preserve one ball owner, then address flight, impact cushioning, release impulse, floor bounce and foot/body weight transfer. Keep source-motion, retarget and consumer findings distinct. Do not simply import the standalone preview's baked ball path into Tactics, which already evaluates its own match ball.

The new Studio catch/pass sequence inherits the source clips' limitations. None of these changes constitutes coaching approval or completion of the realism work.

## Verification

- 10 workspace/catalog unit tests passed, including hidden-ball pose persistence.
- 69 focused browser checks passed: both animation selectors, reduced-motion explicit selection, all relevant ball visibility/scales, a real skinned ball through the sequence join, edited-ball pose restore, all gaits at 1.60/1.75/1.95 m, palm contact within 1 cm, deterministic scrubbing, cadence and loop continuity. The largest ball displacement in a 10 ms sample across the sequence join was 4.44 mm.
- 44 existing Studio browser checks passed, including saved setups, import/export, desktop/mobile and pose controls.
- All 17 clip clocks were audited; 11 slow-frame/pause/scrub checks and 10 exported-rig jump checks passed.
- All 12 native Movement balls passed the existing geometry/motion/deterministic-scrub checks; eight associated phase, one-shot and ball-pose checks passed.
- Catch, transition, pass and carry frames were visually inspected. No application exceptions were reported. The compiled GLB's actual hash still matches the accepted asset.

Receipts and images are in ignored `verification/animation-controls/`, `verification/motion-audit/`, `verification/studio/` and `verification/regression/`. Reproduce with `node tests/animation-controls.mjs`, `node tests/motion-audit.mjs`, the Studio browser harness and the existing playback/jump/movement-library harnesses configured for port 5397. `before.json` retains the dropdown failure; `cadence-before.json` retains the original gait-cadence failure. The hidden-ball unit test was also observed failing before correction.

The model/Blender assets and Tactics runtime source were not modified. Full native Blender and Tactics suites were not rerun. This remains local, uncommitted implementation; no PR, merge or deployment is claimed.
