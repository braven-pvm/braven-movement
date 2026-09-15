# Movement and Tactics: models and integration

Established by Marius on 14 September 2026. This is the persistent lane for shared athlete models and kits, and for using Movement's rigged animations inside real Tactics plays. It works in both repositories. This charter records that direct assignment; it is not a new programme-wide control plane.

## Responsibilities

| Area | This lane owns | Working boundary |
| --- | --- | --- |
| Characters | Editable body masters, runtime models, material variants, skeleton compatibility, skin weights and model-specific retargeting | Preserve editable sources and asset provenance. Motion/science lanes supply technique intent and evidence. |
| Kits | Garment geometry, fitting, weights, seams, skirt/shorts variants, colours and future lettering/customisation | One source asset family usable in Movement and Tactics; consumer presentation can differ. |
| Integration | Import/export adapters, clip/rig compatibility, play-event selection, blends, contact alignment and visual verification on the court | Tactics retains its world evaluator, possession, ball flight, actor paths, rules and clock. |
| Delivery | A reproducible, versioned pairing of models, motion data and consumer code; local builds and acceptance evidence | A newer upstream artifact becomes a candidate first. Successful source checks alone do not establish visual or coaching acceptance. |
| Expansion | Additional models, kits, animation families and sports through explicit compatibility declarations | Netball is the implemented baseline. Additional sports and a general asset registry remain future work. |

Upstream Movement lanes continue to own motion solving, movement-science evidence and technique authoring. This lane owns faithful transfer onto the shared character and useful consumption in Tactics. Fixes discovered during integration should identify whether the defect originates in the source motion, retarget, garment, selection rule or consumer; do not compensate for an upstream defect invisibly in the renderer.

Movement already has character/animation and Tactics-contract briefs in its main checkout's `.remember/`. This direct assignment establishes the shared-character and consumer-integration responsibility here. Existing shared contract work must be reconciled with its current owner before changing that boundary. Do not assume an old task title or historical manager ID identifies today's owner. No current reporting endpoint has been confirmed.

## Read first on resuming

1. [State](STATE.md): exact workspaces, accepted local baseline, evidence and limitations.
2. [Backlog](BACKLOG.md): one shared queue; distinguish proposed work from implementation.
3. [Asset and animation handoff](CONTRACT.md): current mechanics and the intake requirements for subsequent work.
4. [Working procedure and handoff template](HANDOFF.md).
5. Repo guidance for the affected area: Movement's [known issues](../../KNOWN_ISSUES.md) and [architecture](../../ARCHITECTURE.md); Tactics' `CLAUDE.md`, `docs/open-threads.md` and local lane entry at `docs/lanes/movement-tactics/README.md`.

This directory is the canonical lane record. Tactics keeps a consumer entry point, not a second backlog. Update this record in the same work unit as a model/import/runtime change. Current machine paths are in State; they are workspace configuration, not an application dependency.

## Working approach

The working pipeline is **Blender/Python editable sources → glTF/GLB plus motion metadata → Three.js in the Studio and Tactics**. Native Blender sources retain authoring controls that the runtime does not need. Other authoring tools may enter through the same evidence-backed boundary; the earlier [platform evaluation](../../NETBALL_ATHLETE_PIPELINE.md) remains available if requirements justify a different route.

Keep work bounded around an observable outcome: for example, a named kit stays closed through a specified clip set, or an ordinary drawn pass aligns both athletes at release and catch. Reproduce defects before changing behavior; retain RED/GREEN evidence for new behavior, then inspect the actual model in both relevant surfaces. Numeric checks and visual judgment answer different questions.

Preserve the current owned worktrees and uncommitted prototype. Before any base update or migration, make a recoverable checkpoint and inspect shared-file changes. Do not use either primary checkout for lane edits. Current authorization covers local development and review; promotion is a separate instruction. The lane setup does not introduce scheduled work or start the proposed backlog automatically.
