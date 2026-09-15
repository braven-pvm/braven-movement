# Braven Studio implementation plan

**Goal:** Maintain the athlete viewer as a useful local internal app for model, kit and animation browsing, verification and showcase use.

**Authorization:** Marius requested the persistent app and confirmed local first, shared hosting next on 14 September 2026. Work continues in the existing owned worktree. No hosting, authentication, PR or production deployment is part of this unit.

**Architecture:** Keep the tested Three.js/Tactics rendering adapter in `athlete/viewer/src/main.js`. Add small catalog, browser-storage and application-controller modules. The catalog contains the actual one model, two garment choices and loaded clips; it can grow without adding fictional assets. Store validated, asset-bound saved review setups locally and support JSON export/import. Build as static files with a reproducible Windows launcher at a stable local address.

**Design:** Braven Studio is a working review desk. A restrained navy header, white library/inspector, teal actions and pale court surround the real athlete. Use Segoe UI for readable controls, left-aligned labels, 8/16/24/32 px spacing, one strong playback action and a large uncluttered model viewport. Library sections are Animations, Kits, Models and Saved. Animation search/category filters sit beside results. Advanced pose controls are disclosed on demand. Review notes are explicitly local; source checkpoints are distinct from coach approval.

**Alternatives considered:** A separate React application would duplicate the viewer before it adds value; embedding the unchanged prototype would preserve its usability problems. Extend and separate the existing app's catalog/state/UI responsibilities now, leaving shared hosting and storage for the next phase.

## Work units

- [x] Preserve the current viewer source in an external archive. Add tests for catalog filtering, versioned persistence, invalid/imported data and model compatibility. Initial new-module failure was an import failure; later model-isolation/recovery tests failed behaviorally before correction.
- [x] Implement catalog and storage modules, with local recovery/error feedback and no shared-approval claims. Nine unit tests passed.
- [x] Build the library/stage/inspector interface. Retain existing animation/kit/pose controls and integration test hooks. Add playback shortcuts, frame stepping, saved setups including pose/camera, notes and snapshot/export/import.
- [x] Add a stable launcher/build identity and clear local operating instructions. Keep the accepted POC package intact.
- [x] Run the production build, 44 actual browser checks, reload/import/persistence/error cases, desktop/mobile visual inspection, 11 clock and 10 jump regression checks. Update lane state and backlog with exact scope/results.

## Acceptance

Browse/search every loaded animation, switch both real kits on the same body, inspect model/source status, play/pause/scrub/step at 1x, save a named setup and note, reload and restore it including an edited pose, export/import it, recover from invalid input without losing saved work, and reopen the compiled app through its launcher. Confirm no horizontal overflow on a phone and preserve actual bone animation and timing. No new source model/clip or server-side team persistence is implied.
