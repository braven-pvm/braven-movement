# Working procedure and handoff record

## Resume and choose the next unit

1. Read the lane [State](STATE.md), [Backlog](BACKLOG.md) and current guidance in both affected repos. Confirm the latest user assignment; do not restart the original platform investigation or assume all proposed backlog items are active.
2. In each owned worktree, inspect `git status --short`, branch, HEAD and diff. Reconcile the actual filesystem with State. Preserve inherited changes. Before updating a base, make a recoverable checkpoint and inspect incoming changes in shared files.
3. Identify upstream motion, character or contract changes needed by the unit. Use source commits/artifacts and current ownership evidence, not historical task names. For an actual shared-file/contract collision, prepare the exact decision needed before escalating. Ordinary reversible lane work does not need repeated permission.
4. Write one small acceptance statement and its cross-repo dependencies. Keep work in this lane's owned checkouts. Update State/Backlog when work starts and when evidence or limitations change.

## Intake and implement

1. Obtain a pinned candidate with the [handoff contract](CONTRACT.md). Check artifact hashes and the declared technique/variant semantics before retargeting. Inspect source checks and unresolved warnings.
2. Preserve the accepted native/runtime package. Make body, kit and retarget changes in editable sources; export to an explicit directory outside the source repository. Use a separate candidate directory when comparing with an accepted revision.
3. Import the exact candidate into the owned Tactics worktree and regenerate the sidecar. Never hand-edit sampled contact arrays to hide a model/export discrepancy.
4. For behavior changes, reproduce the failure with the smallest meaningful test, record RED, implement and record GREEN. Report pre-existing tests or provenance that were not checked. Documentation-only changes need document/path/diff verification, not Blender or full application suites.

## Verification and delivery

- **Asset changes:** inspect native editability, skin weights, required bones, finite/changing clips, material/garment roles, licenses and hashes. Run the affected asset, seam, retarget or jump checks listed in [athlete/README.md](../../../athlete/README.md). Blender integration is passed only when it actually ran.
- **Runtime changes:** use focused tests for event selection, timing, contacts, blending and scrubbing, then the relevant broader suite/build. Tactics commands and browser harnesses are in its local lane entry. Test real user gestures; store injection alone is not court verification.
- **Visual review:** inspect Studio and the actual Tactics play as applicable, including front/side/back garment views, release, first contact, load, take-off, apex, landing and fast catch-to-pass transitions. Review the full body, fingers, ball and clothing together. Check physical pace at 1x rather than relying on slow preview playback.
- **Evidence:** attach receipts/screenshots to exact asset and code identities. Separate passed, failed, skipped and not checked. Keep source checks, visual acceptance and coaching approval separate. A candidate with unresolved defects is not silently promoted to the accepted baseline.
- **Local review:** start the relevant build and verify its actual URL and workflow before handing it to Marius. State what changed and the remaining limitations. Existing authorization covers local implementation; commit/PR/promotion instructions are handled when given.
- **Record:** update the lane's State and Backlog plus affected build documentation. Record a producer/consumer pair, not just the last repo edited. Archive or regenerate package receipts when the package changes; a docs-only edit must not rewrite the historical receipt to imply a new runtime build.
- **Recovery:** restore the prior model, source metadata, generated sidecar and compatible consumer implementation together. Never combine a previous model with newer unverified contact data. Preserve the failed candidate and evidence for diagnosis.

## Copy for a new work unit or upstream intake

```text
Work item / requested outcome:
Status: proposed | active | awaiting dependency | ready for local review | complete
Assignment source and date:
Repo(s), owned worktree(s), branch(es), base SHA(s):
Implementation identity: commit(s), or base plus archived dirty patch/hash:
Affected files and shared-file/contract owners:
Upstream dependency: technique/variant, source commit, job/config/tool hashes:
Candidate identity: model, kit, sport, rig/clip compatibility and artifact hashes:
Editable source and generated output locations:
Changes to units, rig, root travel, timing, phases, contact or release:
License and source-review status:
Acceptance statement:
RED evidence / GREEN evidence / existing provenance not audited:
Verification: passed / failed / skipped / not checked, with receipt paths:
Visual review: surfaces, poses/events, screenshots and unresolved issues:
Coach review status (separate from source or visual checks):
Review URL, exact action and expected result (confirm server first):
Previous accepted pair and recovery procedure:
Next owner/action; backlog and state updated:
```

This template is a working record, not a requirement to fill irrelevant fields. Mark an inapplicable check explicitly and explain material omissions. Do not invent a manager ACK or claim cross-lane approval that has not occurred.
