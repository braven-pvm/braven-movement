# Authored Jog repair — 14 September 2026

**Follow-up:** the user's subsequent video demonstrated a separate backwards-knee failure in normal moving catches. This standalone Action repair did not resolve that reported path; see [moving-catch correction](MOVING-CATCH-REPAIR.md) for the actual runtime cause, signed-bend regressions and current build identities. The notes below describe the earlier, narrower correction.

Marius reported broken-looking legs and ankles in Jog while Run looked correct. Reproduced the native `Jog` at port 5397 and on the Tactics court; compared it with the ordinary `jog` and `run` locomotion paths. The affected animation was the authored GLB Action.

The original FK helper aimed every foot toward a fixed forward vector after folding its parent shin. That closed the shin-to-toe angle to **13.10 degrees** and could turn the shoe over: aiming a direction alone did not constrain the roll. `athlete/motion.py::jog_leg` now constructs leg orientations from their rest frames with a stable bend plane, and lets the foot follow the recovering shin with bounded ankle flex. `correct_jog.py` rebakes only Jog into a fresh editable candidate.

The cycle remains **1.0333333 seconds**. The two exported ankles measure **102.45–137.98 degrees** through 496 between-key browser samples. These are geometry checks for this repair, not a biomechanical or coaching certification. Further foot-contact timing and toe/heel articulation can still improve the demonstration.

## Artifacts and running apps

- External candidate: `Netball Athlete/candidates/08-jog/`; revision 7 is preserved alongside it.
- GLB SHA-256: `55c611f1a525c1ec873dfe2aa01970f806c1090c9081973ac14ca1148847a412`.
- Studio: http://127.0.0.1:5397/?build=1953e5ad, build `1953e5adc1cd7104dbb6be4f1fb00c1fc448d39a80c93a62d0410c13cb48bbc8`.
- Tactics: http://127.0.0.1:5396/, build `mu1ab8gg df62c37-dirty`; dev source remains at 5395.
- Source recipe: `athlete/correct_jog.py` plus `motion.py`; copies are beside the new `.blend` and GLB. The phenotype source, 17 Actions and four editable IK targets are retained.
- Tactics reimports the asset and regenerates its contact sidecar. Its optional offline model cache now uses the imported asset hash, preventing an existing installation from reusing the old model after a worker update/reload.

## Verification

- `python athlete/verify_jog_asset.py --before <07 GLB> --after <08 GLB> --report <receipt>`: the other **16 exported animations are exactly unchanged**, as are every mesh vertex attribute and skin weight. The native rebake also asserts that all other Action curves are unchanged.
- Tactics: **3,220 tests passed**, **one optional fixture emitter skipped**. Three new actual-GLB cases sample both legs at 249 points at heights 1.60, 1.75 and 1.95 m: ankle range/roll, knee bend, fixed joint offsets, rotation continuity and matching loop endpoints. The new ankle test failed on revision 7 before correction. The full run exposed a comparison artifact from non-unit Float32 quaternion copies; normalizing those comparison copies resolved it. Type checking then caught two test annotations; corrected and the three focused tests plus build passed.
- Studio: `node tests/jog.mjs`, **seven browser checks passed**. Real selection autoplay, geometry, cadence, both kit buttons, front/side scrub screenshots, looping and no exceptions. The initial harness used a nonexistent kit select; changed it to the actual kit buttons before the successful run.
- Native Blender: **14 editability/IK/GLB round-trip checks passed**; seam and GLB structure/weights checks passed.
- Compiled Tactics: **three Jog browser checks** passed through the actual picker/demo/play controls, including a stale previous-model cache entry; **five package checks** passed for build identity, real play, exact model hash, offline reload and no exceptions. The first Jog harness wrongly searched DOM text for a canvas-drawn project title; the successful run waits on the actual timeline readout.
- Browser evidence: `athlete/viewer/verification/jog/` and Tactics `verification/athlete/jog/`. Front and side poses were visually inspected with both kits, including swing and recovery phases.
- The broader prior physics, timing, footwork and ordinary-pass browser suites were not all rerun for this Jog-only asset correction. Their clip channels are covered by the exact exported-data comparison; no new blanket pass claim is made for those suites.

In Studio select **Jog**; use **Side** and **Front**, switch between **Skirt + shorts** and **Shorts**, and play or scrub a full cycle. In Tactics choose **Braven Movement → Movement clip → Jog → Open clip demo**, then Play. The existing Run locomotion code and capture data are unchanged.

Changes remain local and uncommitted in both owned `codex/netball-athlete` worktrees.
