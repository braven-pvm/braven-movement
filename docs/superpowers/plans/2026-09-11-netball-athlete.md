# Editable Netball Athlete Implementation Plan

**Goal:** Deliver one working, animated, realistic female netball athlete with editable model, rig, pose, kit and Tactics control.

**Architecture:** Independent Blender/Python authoring exports a modular skinned GLB and editable Blend file. A Three.js workbench loads the GLB and imports the actual Tactics retarget/pose code from a configured checkout. A small opt-in Tactics adapter preserves authored garments and materials.

**Tech stack:** Installed Blender 4.5 LTS / MPFB, Python 3.11+, Three.js 0.169, Vite 8.3.

**Spec:** `docs/NETBALL_ATHLETE_PIPELINE.md`; user confirmed realistic female athlete and explicitly requested a fresh perspective and a working result.

## Global constraints

- Work in isolated Movement and Tactics worktrees; preserve primary checkouts.
- Generate assets outside source trees, retain editable master and runtime export.
- No dependence on the old Movement pose/render/kit pipeline.
- Use real skinned garment meshes and the actual Tactics retarget code.
- Do not equate an animated demonstration with coach-approved netball technique.

## Task 1: Editable source and portable asset

- [x] Add a meaningful GLB integration verifier that fails on absent/missing joints, static animation or unskinned garments.
- [x] Create `athlete/build.py`, `athlete/garments.py` and `athlete/motion.py`: build fresh MPFB human, custom mesh kit, pose/IK controls and distinct animation clips.
- [x] Run Blender; inspect source, skinning, geometry and exported animation numerically and visually. Save generator inputs and source licences in a manifest.

## Task 2: Interactive control and Tactics connection

- [x] Add a small tested Tactics authored-asset path: preserve textures, select mesh kit, avoid adding duplicate hair/skirt, and allow an opt-in female figure URL.
- [x] Build `athlete/viewer/`: a quiet, full-height studio view with a clearly grouped side panel for Animation, Kit and Pose; mobile stacks controls below the model.
- [x] Expose play/pause, speed, scrub, clip selection, bone rotation, skeleton/wireframe, colours and pose export/import. Use no fake compatibility indicator.
- [x] Run Tactics mode against its real `buildSkinned`, `pose` and `applySkinnedPose` exports.

## Task 3: Verification and delivery

- [x] Validate Blender/GLB round trip, weights, animation displacement and joint contract.
- [x] Exercise browser controls, multiple animation times, kit changes, bone edits, responsive layout and errors in Chrome.
- [x] Run relevant Tactics tests/typecheck and Movement host suite. Record skipped coverage separately.
- [x] Leave the working model and local review URL available; document exact rebuild and launch commands and observed limitations.
