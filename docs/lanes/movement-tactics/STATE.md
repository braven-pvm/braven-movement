# Lane state

Recorded 14 September 2026 during lane organisation. Documentation setup changed no model or runtime behavior. Source state and existing receipts were inspected; the historical suites below were not rerun for this documentation change.

## Current development: Braven Studio

**Publication handoff, 15 September:** Marius requested commits and PRs into both
repositories' `main`, with deployment left to Tactics, and requested the local dev
panel be hidden first. Both branches are being refreshed against current `main`.
Tactics now includes the reviewed athlete in its standard production build; the
dev panel is restricted to its Vite development server and absent from compiled
packages. The native revision 8 asset and shared jog correction remain the paired
implementation. Historical uncommitted/build statements below describe the earlier
local review stages rather than the publication handoff.

**Latest jog contact/cadence correction:** Marius found the prior joints better but the athlete still appeared to skate. Ordinary jog and moving catch used different strides, the locomotion base sometimes put support beyond reach, and sole vertices inherited calf weights. One distance cycle now drives jogging and its ball actions; court contacts remain fixed, the base respects leg reach, and the shared loader corrects sole binding on a per-rig geometry clone. Native revision 8 is unchanged. **3,230 Tactics tests passed / one optional fixture emitter skipped**, ten real Jog/Move/Flat-pass browser checks, three compiled import/playback checks and eleven Studio checks passed. Fixed-camera plain jog, stop, front and moving-catch frames were inspected. Tactics **mu1cw0rh**, Studio **7f1e6944**. [Evidence, review steps and limits](../../../athlete/viewer/JOG-CONTACT-SYNC.md). This remains local/uncommitted and awaits visual acceptance; **mu1bosts** is archived under `08-jog/revisions/tactics-before-contact-sync/`. Older identities below are historical.

**Latest deeper jog review:** reproduced discontinuous gait changes on real drawn paths, inherited knee roll, excessive swing-ankle flexion and a hard IK extension limit. Added continuous athlete gait blending, retained lateral pose components, and solved leg frames/soft extension/recovering shoes. **3,226 Tactics tests passed / one optional fixture emitter skipped**, eight real Jog/Move/Flat-pass browser checks, three compiled Jog import/playback checks and eleven Studio checks passed. Side/front frames were inspected. Tactics **mu1bosts**, Studio **c5ac2f99**; native revision 8 is unchanged. [Evidence and limits](../../../athlete/viewer/GAIT-DEEP-DIVE.md). This is a local candidate awaiting Marius's visual acceptance; the preceding runtime is archived in `08-jog/revisions/tactics-before-gait-dive/`.

**Latest video follow-up:** the standalone Jog fix below did not resolve Marius's normal moving-receive issue. Reproduced backwards knees in `applyAthleteFootwork`: projecting the stationary source knee onto a travelling leg flipped the IK bend direction. Corrected to the anatomical forward plane. New signed-bend regressions failed before/passed after; final **3,223 tests passed / one optional skip**, eight real Move/Pass browser checks, three compiled imported-play checks and 11 Studio footwork checks passed. Current Tactics **mu1an7c1 df62c37-dirty** (5396), Studio **4b4de6cf** (5397). Native GLB revision 8 is unchanged. [Cause, verification gap and delivery](../../../athlete/viewer/MOVING-CATCH-REPAIR.md). The preceding compiled runtime is preserved in revision 8's `revisions/tactics-before-knee-fix/`. Work remains local/uncommitted.

Latest correction, 14 September: native **Jog** forced the recovering foot toward a fixed world-forward vector, closing the ankle and allowing shoe roll. Revision **8** rebakes this one Action from stable leg frames with a shin-relative foot; the other 16 exported Actions and all mesh attributes/weights are exactly unchanged. Candidate `Netball Athlete/candidates/08-jog/`, GLB `55c611f1a525c1ec873dfe2aa01970f806c1090c9081973ac14ca1148847a412`. Studio **1953e5ad** at 5397; compiled Tactics **mu1ab8gg df62c37-dirty** at 5396. Tactics now keys its offline athlete cache by asset hash. Native editability/seams/weights, seven Studio Jog browser checks and **3,220 Tactics tests** passed (one optional fixture emitter skipped). See [Jog repair and verification](../../../athlete/viewer/JOG-REPAIR.md). Both owned worktrees remain local/uncommitted; revision 7 is preserved. Earlier entries below record their respective stages.

Latest follow-up: Marius accepted the revision 7 realism pass and asked to proceed with travelling foot plants/pivots. MTI-004 now has a local implementation: shared path-derived leg targets, settling after a drawn run, a planted right support during a turn and a moving-receive scenario in both Studio and Tactics. Studio build **`8c749a42487e31e32a1ebd71f052e2af01d22efaf7edf184bc6cc6aa22493f3b`** remains at port 5397. The revision 7 GLB is unchanged. Final Tactics suite: **3,217 passed, one optional test skipped**; Studio: **11 unit, 11 footwork, 44 existing Studio and 69 animation-control checks passed**. See [footwork report](../../../athlete/viewer/FOOTWORK.md) for scope, reproducible review steps and remaining momentum/landing-foot work. Earlier stage identities below remain historical records.

Current compiled Tactics: **`mu17seh9 df62c37-dirty`**, port 5396, same candidate package folder. Seven footwork, 14 ordinary-pass and five compiled/offline browser checks passed. The preceding runtime package is retained under `candidates/07-realism/revisions/tactics-before-footwork/`. Both worktrees remain uncommitted.

Later on 14 September, Marius selected the persistent internal app as the first development unit and confirmed **local first, shared hosting next**. MTI-010 is complete locally. The maintained source is `athlete/viewer/`, with a stable launcher `athlete/Open-Braven-Studio.ps1` and URL **http://127.0.0.1:5397/**. It is a compiled static app with browser-local, model-version-specific persistence, not shared team storage.

The app contains the actual one model, two kit choices and 17 animations; search/category filtering, source-review details, playback/frame/phase controls, advanced pose editing, saved setups/notes, workspace import/export and image capture. The original external POC package and native revision 6 model remain intact. Pre-app viewer source was archived under the external output's `revisions/studio-before-app/`.

Current build identity: `3d7d59f40796eb206d9094620d49a8c1b3105040965a5bccf3e8c3ce100ed5b4`. MTI-012 (autoplay, balls and speed checks) remains complete. Marius then authorized MTI-013: its first local realism candidate is **revision 7**, GLB `ec305d0203331ef77c69eb159db66c086ffbe4345eea6fe5e360b930930f6865`, 17,089,224 bytes. It is now loaded in Studio and imported into the companion Tactics worktree with a regenerated contact sidecar. Free-flight ball gravity is independent of body retargeting; dedicated preview throws match Tactics speed settings; the bounce includes floor impact; five grounded catches add a small authored absorption response with stable feet and grips. Native master, phenotype, recipe and receipts are under the external output's `candidates/07-realism/`.

Current verification: **42 realism checks, 10 unit tests, 44 Studio browser checks, 69 animation-control browser checks, all 17 clip clocks, 11 slow-frame playback checks, 10 exported-rig gravity checks and all 12 native technique-ball checks passed**. Blender editability/IK/round-trip, GLB weights and seams also passed. The Tactics suite was rerun: **3,209 passed, one optional fixture emitter skipped**; athlete build and 14 real-court pass checks passed. See [realism report and limits](../../../athlete/viewer/REALISM.md), including the corrected interpretation of the earlier pre-contact averages and the initial failures/rechecks.

Implementation remains local and uncommitted in the same worktrees. Revision 7 is ready for visual review; the accepted revision 6 and historical receipts below remain preserved. MTI-013 is a first bounded realism pass, not completion of travelling foot plants, contextual receiving, full-body physics or coaching review. Tactics retains one authoritative match ball and its existing selection/flight rules. MTI-011 retains shared hosting/access and team review storage.

Revision 7's compiled Tactics package is also running at `http://127.0.0.1:5396/`, build `mu16vbnw df62c37-dirty`, from `candidates/07-realism/tactics/`. Four compiled playback/hash/offline/browser-error checks passed. Use that candidate folder's `Open-Braven-Tactics.ps1` to reopen; the root's older packaged launcher still addresses the historical revision 6 files.

## Workspaces and recoverability

| Role | Owned worktree | Branch | HEAD / prototype base |
| --- | --- | --- | --- |
| Movement authoring and canonical lane record | `F:\Repositories\braven-movement-netball-athlete` | `codex/netball-athlete` | `5a65dfc357e6815849495ef2b2c52eec5227e5e9` |
| Tactics consumer | `F:\Repositories\braven-tactics-netball-athlete` | `codex/netball-athlete` | `df62c37073cdcad3f584789a5bdb07fff08a484a` |

Both contain staged, uncommitted prototype implementation inherited from the preceding work. The lane documents are additional local changes. A HEAD SHA alone does **not** identify this implementation. Do not reset, clean, switch branches or recreate these worktrees on the assumption that HEAD contains the delivered prototype.

Primary checkouts `F:\Repositories\braven-movement` and `F:\Repositories\braven-tactics` are for discovery only. Other lanes use them and other worktrees. Existing main-checkout `.remember/LANE-BRIEF-character-and-animation.md` and `.remember/LANE-BRIEF-tactics-contract.md` provide upstream context; do not rewrite their global state as part of this lane.

Cached `origin/main` at inspection: Movement `16246780f3e0c88ace7a973ca5c7519d7d041cc7`; Tactics `df62c37073cdcad3f584789a5bdb07fff08a484a`. No remote fetch was performed for setup. Movement has newer contract/provenance work than the pinned technique snapshot below. These references must be refreshed and compared before the next intake; this lane is not claiming to incorporate the latest remote code.

## Accepted local baseline

Marius approved the realistic adult female direction, the lighter complexion and shorter fitted skirt, then the seam, playback-speed and jump corrections. The source remains editable. This visual/product acceptance does not imply that every technique is coach-approved.

| Item | Current baseline |
| --- | --- |
| Model | Revision 6; 17,070,564-byte GLB; 70 deformation controls including fingers, 16 skirt panel bones and `Ball_Control` |
| Native editing | Packed Blender master with 17 Actions and four IK targets; separate phenotype source for body changes |
| Kit | Jersey, binding, shorts and fitted skirt; material controls in Studio; source GS lettering remains fixed |
| Animation | Five general clips plus twelve imported Movement techniques |
| Source technique snapshot | `b4f707478ddea3240110f80b5d8e7373a884cb90` with retained solved jobs and hashes |
| Runtime | Local Tactics athlete mode; automatic throw/catch clips in normal netball plays; manual technique scheduling also supported |
| Native height | `1.7216965637645487` metres before requested uniform scaling |

GLB SHA-256: `32956794e77f6663035b57d0e364fbba70a67e64713725b97fa667faa7b2ba13`.

Native master SHA-256: `4cd588fcf7e4668dd73cc6d6c7aa17b67738251bfa80c4564ec04606a47be96c`.

The manifest and actual files are authoritative; verify hashes before rebuilding or reporting a delivery. Source checks pass for seven imported techniques. Five need review: high deflection, jump catch/pull-in, one-hand snatch/transfer, chest catch and two-hand snatch/straight-back. None is coach-approved on this athlete.

## Current selection and synchronization

- A Flat pass uses the existing planned-distance rule: below 6 m selects chest; 6 m or farther selects shoulder/one-hand high pass. Explicit chest or shoulder selection overrides that rule. Bounce uses the bounce throw; Lob/overhead uses the overhead throw. This is the prototype's current rule, not a general sports-science recommendation.
- The actual receiving actor uses `netball_two_hand_snatch_pull_in`, including interceptions and catches before planned arrival. There is no automatic high/low/wide/jump/one-hand catch selection yet.
- Explicit scheduled techniques take precedence. Catch contact is retained before blending into the next throw; the throw's authored release remains aligned with the pass event. Deleting the pass removes the derived catch, and an interrupted catch does not resume afterward.
- Tactics owns one match ball. Model-specific sampled grip positions align its held state and flight endpoints. The model's demonstration ball is hidden on the court. Player paths own horizontal travel; clip vertical movement is retained.
- Absolute-time sampling supports scrubbing and playback-speed changes. Corrected jumps use ballistic vertical timing. General jump flight is approximately 0.424 s; jump catch 0.300 s; double-foot landing 0.383 s.
- Local athlete mode enables the library for new and opened netball plays. The saved standard-motion opt-out is retained. A manually added technique does not create a ball/pass event.

Upstream contract briefs record a chest-pass default ruling. Its interaction with this distance heuristic must be reconciled against current upstream code and the intended ordinary-pass behavior before changing selection. Do not silently equate these two policies.

## Known limitations and next intake

Contextual receiving, foot planting while travelling, arbitrary body retargeting, variable bib lettering, a per-sport model registry, facial animation, cloth collision and production LOD/performance work remain unfinished. Extreme poses may need garment corrections. Current native model loading uses an environment override; it is not yet a general model/kit/sport selection system.

There are two integration paths to reconcile: existing Movement compact technique clips and the prototype's full native GLB clips with a generated sidecar. Their fields and guarantees are not interchangeable. Newer upstream kit and clip/provenance changes are candidates for intake, not automatic replacements for the accepted asset. See [Backlog](BACKLOG.md).

## Artifacts and local entry points

Artifact root (external to both repos):

`E:\cloud services\OneDrive - About IT Group (Pty) Ltd\Documents\ChatGPT\Braven Movement\Netball Athlete`

- Sources/assets: `netball-athlete.blend`, `athlete-source.blend`, `netball-athlete.glb`, `manifest.json`, `movement-library.json`, `movement-library/`.
- Packaged surfaces: `studio/` and `tactics/`; earlier models under `revisions/`.
- Receipts: `package-receipt.json`, `tactics-build-receipt.json`, model verification JSON and screenshots. Tactics also retains browser receipts under its worktree's `verification/athlete/`.
- Studio: `http://127.0.0.1:5393/?revision=6`; Tactics development: `http://127.0.0.1:5395/`; compiled local Tactics: `http://127.0.0.1:5396/`. These are launch addresses, not a promise that a server is running. Check before sending a review URL.

The recorded packaged Tactics build is `mu13a3gx df62c37-dirty`. The package receipt's Tactics patch hash is `62e25cff178e5ba1d571034f71467ce9675e928c46dcc5d51b839f7fcb61aa02`. It identifies the archived prototype patch, not subsequent lane documentation. No merge or production deployment is part of this baseline.

## Recorded verification

| Evidence | Recorded result | Scope / qualification |
| --- | --- | --- |
| Tactics unit suite, 14 September 12:17 SAST | 3,209 passed; one skipped | Optional fixture emitter skipped; previous implementation run, not rerun for lane setup |
| Tactics athlete build | Passed | TypeScript, Vite and service worker; non-failing bundle-size advisory |
| `verification/athlete/ordinary-passes.json`, 14 September | 14 checks passed | Actual court Pass circles for Flat/Bounce/Lob, both rigs, quick return, grip/trajectory alignment and real playback |
| `verification/athlete/package-browser.json` | Four checks passed | Compiled normal netball template, playback, model hash and offline reload after first use |
| Revision 6 Movement delivery | Native, baking, garment, gravity and Studio checks recorded | Detailed counts and limits in [athlete/VALIDATION.md](../../../athlete/VALIDATION.md); earlier broad legacy coverage is separately labelled there |

Historical checks are not proof for a changed artifact. Failures, skipped coverage and unchecked areas must remain distinct. Source numerical checks are not coaching approval. Prior RED/GREEN traces are not all archived as standalone files; baseline TDD provenance has not been fully audited. New behavior work must retain its own evidence without pretending this baseline is entirely reverified.
