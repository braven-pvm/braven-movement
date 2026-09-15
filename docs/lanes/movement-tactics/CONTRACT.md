# Shared asset and animation handoff

This is the lane's human-readable intake contract. It describes the working prototype and requirements for future deliveries. It is **not** a newly implemented runtime schema. Existing [Tactics clip contract](../../TACTICS_CLIP_CONTRACT.md) and [figure boundary](../../THE_FIGURE_AT_THE_TACTICS_BOUNDARY.md) documents describe another established path; check their current code and owner before changing shared vocabulary or rig assumptions.

## Ownership and flow

```text
Movement motion/science lanes -> solved motion, phases, provenance and review status
                                             |
This lane in Movement -> editable character/kit -> retarget and verify -> immutable export
                                                                            |
This lane in Tactics -> import exact export -> select/sample/blend -> real play + one ball
```

Blender sources retain body, garment, weights, controls and editable Actions. Runtime exports are derivatives. A kit or animation fix must be traceable to its source; editing only a generated export is not a reproducible delivery.

## Current implemented boundary

| Concern | Current behavior |
| --- | --- |
| Source package | Movement exports GLB, native masters, `manifest.json`, `movement-library.json` and pinned solved jobs. |
| Consumer import | Tactics `tools/import-athlete.mjs` checks the GLB against the manifest, copies the textured asset and source metadata, and generates `src/data/athlete-motions.json`. |
| Identity | Sidecar records the GLB SHA-256 and revision; imported clips retain source commit/job hash and source-check/coach-review flags. |
| Clip data | Exact clip IDs, duration, phase times, release/contact times, anchor and sampled ball transforms. General clips can lack contact/release/source-job fields. |
| Rig | Exact case-sensitive joint names, hierarchy, bind pose and compatible skin weights matter. The current GLB has 70 deformation controls. Blender's four IK targets/constraints stay in the native master. |
| Garments | Separate weighted `Kit_Jersey`, `Kit_Binding`, `Kit_Shorts`, `Kit_Skirt`; skirt panel bones must survive import and blending. |
| Units and transform | Metres and seconds. Tactics court `(x, y)` maps to Three.js `(x, elevation, -y)`. The importer applies the existing model orientation/floor convention and records native height/floor offset. Ball samples are `[time, forward, height, side]` in the adapter's local convention. |
| Root motion | Strip native horizontal pelvis travel so it does not duplicate the actor's authored court path. Preserve intended vertical movement. Apply height/heading consistently to body and grip. |
| Timeline | Sample bones at absolute play time, including fingers and garments. Preserve actual contact/release events through retiming and blending. Authoring frame rate is not playback speed. |
| Ball | `evaluateFrame` remains authoritative for ownership, flight and rules. The imported `Ball_Control` supplies model-specific contact geometry; each model's demonstration ball stays hidden on the board. |
| Selection | Automatic motion derives from real play events; explicit techniques take precedence. Current defaults and missing variants are recorded in [State](STATE.md). |

Changing body dimensions, rest pose, rig, phase timing or the GLB requires regenerating and checking the sidecar. Do not reuse contact coordinates merely because two exports share clip names. Source phase labels may differ from the actual possession-event frame; carry both and test the event frame.

## Required contents of the next handoff

1. **Identity and provenance:** exact source commits, any dirty patch hash, generating tool/config versions, solved-job hashes, output hashes and licenses for body, hair, clothing, textures and motion inputs. A file named “latest” is not an identity.
2. **Compatibility:** intended sport(s), model and kit variant, joint names/hierarchy/rest pose, units, facing direction, scale/height policy, mesh/material roles and supported clips. Report changed assumptions explicitly.
3. **Motion semantics:** named technique and variant, handedness, start/end, contact/release, take-off/landing where applicable, root-travel policy, timing changes and their rationale. Preserve upstream evidence; do not invent human-motion constants to fill missing provenance.
4. **Review state:** source solver checks, retarget fidelity, visual review and coach approval as separate fields/results. Missing or failed checks remain visible. Reference footage is a sample, not universal technique truth.
5. **Evidence and fallback:** representative native/Studio views, court playback and event-contact measurements on the exact export; known limitations; the previous accepted package that can be restored as a complete pair.

Record these in the [handoff template](HANDOFF.md). Some exist in today's manifests; compatibility IDs, rig fingerprints and a general multi-sport registry do not yet exist as enforced runtime fields. Formal schema and validation work is proposed in [MTI-002](BACKLOG.md).

## Rules for future kits, bodies and sports

- Treat a new kit as a fit/deformation change even when it uses the same rig. Check neckline, armholes, waist, hem and undergarment coverage at rest and through overhead, crouch, reach, throw and landing extremes.
- Treat a new body shape as a retarget and garment-fitting change. Uniform runtime height is not a new anatomical model. Regenerate grip data and check feet, ball contact and both sides at several headings/heights.
- Add a sport by declaring its applicable assets, technique semantics and selection rules. Keep sport-specific choices in Tactics' sport/data boundary. Do not silently reuse a netball kit or catch for every feminine model or sport.
- Keep manual technique choice available as automatic selection expands. Contextual selection needs explicit, testable reasons such as authored pass type, arrival height/direction or movement state. Random variety is not a substitute for a suitable movement.
- A shared contract change needs a producer/consumer migration decision before implementation. List the impacted files and coordinate their owners; do not independently change compact-clip fields, units, rig names or ball anchors on one side.
