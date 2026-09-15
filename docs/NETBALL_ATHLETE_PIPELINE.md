# An editable netball athlete

11 September 2026. Fresh evaluation for one working character, rather than an extension of the earlier pose-calibration pipeline.

## Decision

Use **Blender + Python to author the character, GLB to deliver it, and Three.js / Braven Tactics to drive it**. These are complementary tools. A game engine does not by itself supply a realistic, editable athlete, fitted garments, or good animation.

The deliverable is an adult female athlete with a fully editable Blender file, named deformation bones including fingers, native hand/foot IK controls, separate jersey/shorts/skirt meshes, editable materials, and baked animation clips. A browser workbench exposes animation, kit, skeleton, and bone controls. Its Tactics mode imports the actual Tactics pose/retarget implementation, rather than claiming compatibility from names alone.

The starting human geometry comes from MPFB's editable CC0 assets. This implementation does not import the existing Movement rendering, pose, garment, or calibration pipeline. Kit geometry and animations are authored separately in `athlete/`. The source character remains replaceable.

## Options evaluated

This is a capability and integration comparison based on primary documentation. Only the selected route is implemented and exercised locally; the other engines have not been benchmarked on this machine.

| Route | Character, kit and motion control | Fit for this delivery |
| --- | --- | --- |
| Blender + MPFB + Python | Editable human topology, weights, armature, material nodes, shape keys, constraints and actions. Custom garments can share the rig. | Selected: editable sources and automatic reproducible exports without requiring a new engine. [MPFB](https://static.makehumancommunity.org/mpfb/faq/why_use.html), [Blender glTF](https://docs.blender.org/manual/id/5.0/addons/import_export/scene_gltf2.html). |
| Three.js | Direct access to bones, weights, morphs and animation tracks. Good for procedural posing and browser tools. It needs a character authored elsewhere. | Selected runtime; Tactics already uses it. [Skinning](https://threejs.org/docs/pages/SkinnedMesh.html), [animation](https://threejs.org/docs/pages/AnimationMixer.html). |
| Unity | Animation Rigging provides IK, aim constraints and secondary deformation. A custom mesh and kit can be imported and driven. | Viable for a native simulator. For today's Tactics browser application, an additional runtime or export bridge adds work without creating the athlete. [Unity](https://docs.unity3d.com/Packages/com.unity.animation.rigging@1.3/manual/index.html). |
| UE5 + MetaHuman | Very capable body/face control rigs and full-body IK. MetaHuman exports include combined skeletal geometry. | Strong high-fidelity alternative; requires asset preparation, materials/LOD work and a Tactics delivery bridge. Do not assume Unreal control rigs transfer through GLB. [FBIK](https://dev.epicgames.com/documentation/en-us/unreal-engine/control-rig-full-body-ik-in-unreal-engine), [MetaHuman export](https://dev.epicgames.com/documentation/metahuman/metahuman-creator-export-tool-in-unreal-engine). |
| Character Creator + iClone | Detailed character authoring, custom fitted clothing, editable weights, FBX mesh/motion export, Blender bridge. | Credible commercial upgrade for appearance and artist productivity. Requires software/content licence choices; not necessary for the first working model. [Clothing](https://www.reallusion.com/character-creator/custom.html), [FBX](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/17-Export/Export-FBX.htm). |
| MHR + Momentum / Python | Parametric human, skeleton, skinning, body/face blendshapes and pose correctives; useful for numerical fitting and IK. | Strong solver foundation. Still needs presentation assets, netball kit and runtime integration. [MHR](https://github.com/facebookresearch/MHR). |
| Godot | Direct skeleton pose/rest/animation access and physical bone support. | Viable alternate application engine; does not remove modelling or Tactics integration work. [Skeleton3D](https://docs.godotengine.org/en/stable/classes/class_skeleton3d.html). |
| Babylon.js | Browser skeleton and skinned-mesh pipeline. | Viable browser alternative. Replacing Three.js provides no clear benefit for this single Tactics character. [Skeletons](https://doc.babylonjs.com/features/featuresDeepDive/mesh/bonesSkeletons/). |
| Cascadeur | Animation authoring and physics-assisted tools with character and animation import/export. | An optional motion authoring stage, not the source of netball kit or the browser runtime. [Documentation](https://cascadeur.com/help/category/190). |
| Mixamo | Automatic humanoid rigging and reusable animations. | Useful motion input, followed by retargeting and editing. Does not solve custom kit or netball-specific technique. [Adobe FAQ](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html). |
| Houdini KineFX / Maya / custom artist | Established DCC rigging, deformation and procedural or hand-authored asset workflows. | Viable authoring substitutes, with additional tool/artist setup. KineFX is documented as a character workflow. [SideFX](https://www.sidefx.com/docs/houdini/character/kinefx/index.html). |
| Python-only procedural geometry | Complete numerical control over geometry and animation. | Useful for rig/garment generation and validation. Building a credible human mesh from primitives would spend effort on anatomy and topology already available in editable form. |
| AI-generated meshes / video-to-motion | Potential sources of shapes or motion to clean and retarget. | Candidates for inputs, not evidence of an editable production rig. Topology, weights, hands, motion and asset rights need validation for each actual output. |

## Ownership and portability

The `.blend` is the editable master; the GLB is a runtime delivery format. GLB carries meshes, materials, skeletons, skin weights, morph targets and animation tracks. Blender modifiers, IK constraints, Python drivers and cloth simulation are not equivalent runtime features: retain those in Blender and bake motion when exporting.

For arbitrary interactive Tactics poses, the skirt uses weighted geometry and explicit panel bones. This is responsive clothing deformation, not a physical fabric simulation. An offline cloth bake is a separate option for authored films; it cannot automatically adapt to an arbitrary new browser pose.

The selected MPFB source assets declare CC0. MakeHuman explicitly separates the graphics licence from the GPL add-on code and permits closed-source use of generated core assets. Repository-authored source and garments remain Braven's work under the repository's existing licensing position. [MPFB asset licensing](https://static.makehumancommunity.org/about/license.html).

The first animations demonstrate technical control. They are authored demonstrations, not motion capture or coach-approved technique.

## Acceptance evidence

Required: actual skinned vertices move across animation samples; all Tactics-required bones are skin joints; skirt and shorts switch without changing the athlete; pose controls affect the selected skeleton; animation time can be scrubbed and paused; Blender reopens the source; browser has no application errors; a real Tactics retarget call animates this asset. Verification results and reproducible launch instructions live in `athlete/README.md` and the generated report.
