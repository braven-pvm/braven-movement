# Braven Movement

Standalone authoring and verification tools for anatomically credible sports-movement media.
The current vertical slice creates an MPFB athlete in Blender, poses a two-handed netball catch,
renders reference views, exports FBX/GLB/Blend files, and writes a hash-backed JSON receipt.

## Current status

This repository is an **authoring/calibration tool under active development**. The pipeline and
portable configuration boundary are working. The hand orientation is visually approved and the
camera/arm geometry has reached review quality, while the complete coaching sample still requires
final visual acceptance. See
[`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md) before using any generated pose.

## Repository boundary

Everything required from this project lives in this repository:

- Python source and contracts are at the repository root.
- Versioned movement inputs are in [`config/`](config/).
- Setup, architecture, known limitations, and licensing notes are in [`docs/`](docs/).
- Local reference images belong in [`references/`](references/) and are intentionally untracked.
- Generated files must be written to an explicit output directory outside the source tree.

The code does not import the Flutter application, depend on a parent checkout, or contain a
user-specific path. Copying or cloning this repository is sufficient to move the development
workspace.

## Requirements

- Python 3.11 or newer for host-side contracts and tests. There are no PyPI runtime dependencies.
- Blender 4.5 LTS with MPFB installed and enabled. Verified locally with Blender 4.5.12 LTS and
  MPFB build 20260722 / reported generator 2.0.17.
- Cascadeur 2026.2 is optional and only needed for the Cascadeur-to-GLB path.

MPFB is loaded from Blender's user extension directory. Do not use `--factory-startup` for the
MPFB generator because that disables the installed extension preferences.

## Verify the host-side contracts

```powershell
.\scripts\test.ps1
```

Equivalent command:

```powershell
python -m unittest discover -s tests -v
```

The Blender/MPFB integration is deliberately opt-in because it creates a full model and exports
several files:

```powershell
.\scripts\test-blender.ps1
```

## Generate the reference catch

```powershell
.\scripts\render-reference.ps1 `
  -Output (Join-Path $env:TEMP 'braven_movement_reference')
```

To use another versioned configuration:

```powershell
.\scripts\render-reference.ps1 `
  -Config .\config\reference_catch.v1.json `
  -Output (Join-Path $env:TEMP 'braven_movement_reference')
```

The generator records the configuration path, schema version, and SHA-256 in its receipt. Passing
`--reference-compared` is an acceptance assertion: use it only after a human has compared the
render to the named reference and the pose is anatomically credible.

## Configuration

[`config/reference_catch.v1.json`](config/reference_catch.v1.json) is the single source of truth
for the current movement ID, reference provenance, pixel landmarks, anatomy limits, 3D pose
targets, regulation-scale netball, camera views, training kit treatment, studio background, and
lighting rig. `reference_pose_config.py` validates and loads it relative to this repository,
independent of the current working directory. The generator uses MPFB's bundled shorts-and-shirt
outfit, sports trainers, ponytail, skin, eye, eyebrow, and eyelash assets and records each source
asset hash in the receipt.

The reference image itself is not committed. Place an authorised local copy at the configured
`reference.assetFile` path when visual comparison is required. The configured SHA-256 and image
dimensions identify the exact source used to define the landmarks.

## Other pipeline tools

The original Cascadeur/GLB mechanism remains available:

```text
Cascadeur GUI -> animated GLB -> job.json -> headless Blender -> PNG + hash receipt
```

- `cascadeur_glb_export.py` requests an animated GLB from Cascadeur's local script server.
- `movement_contract.py` inspects GLB animation data and validates receipts.
- `blender_glb_render.py` normalises and renders a job's GLB.
- `blender_probe.py` verifies real Cycles and EEVEE RGBA rendering.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the component and extraction contract.

## Licensing

The repository does not yet declare a source-code licence. Model/output licensing and reference
image rights are separate concerns; see [`docs/LICENSING.md`](docs/LICENSING.md).
