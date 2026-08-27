# Architecture and portability contract

## Purpose

Braven Movement owns the offline authoring boundary between movement references and immutable
rendered media. A consuming application should receive exported GLB/PNG files plus receipts; it
must not need Blender, Cascadeur, MPFB, pose logic, or reference landmarks at runtime.

## Data flow

```text
authorised reference image
        +
versioned JSON movement config
  (athlete + pose + presentation)
        |
        v
Blender + MPFB pose generator
        |
        +--> deterministic studio PNG views
        +--> neutral and posed FBX
        +--> animated GLB
        +--> JSON receipt with hashes and anatomy/calibration evidence
```

The optional Cascadeur path produces an inspected animated GLB and a `job.json`; the generic
Blender renderer consumes that job without knowing the source scene.

## Components

| Component | Responsibility | External dependency |
|---|---|---|
| `reference_pose_config.py` | Load and validate versioned movement configuration. | Python standard library |
| `reference_pose_calibration.py` | Pixel-landmark comparison and calibration math. | Python standard library |
| `reference_pose_contract.py` | Validate generated pose receipts. | Python standard library |
| `blender_mpfb_reference_catch.py` | Create, pose, express, render, and export the MPFB athlete. | Blender Python, MPFB, and Faceunits 01 |
| `movement_contract.py` | Inspect GLB files and validate render/job evidence. | Python standard library |
| `cascadeur_glb_export.py` | Communicate with Cascadeur's local script server. | Running Cascadeur script server |
| `blender_glb_render.py` | Render an inspected GLB job. | Blender Python |

## Portability rules

1. Production code may import only the Python standard library, sibling modules in this
   repository, or APIs supplied by Blender/MPFB.
2. Default configuration paths resolve from `__file__`, never the process working directory.
3. No source path may point into `braven-training`, a parent checkout, or a named user's profile.
4. Input media is supplied explicitly or resolved beneath `references/`; it is not silently copied
   from temporary attachment locations.
5. Generated artifacts go to a caller-supplied directory and are never treated as source.
6. Athlete phenotype, readiness, expression, pose, camera, material colours, ball construction,
   studio colours, and lighting remain versioned configuration or deterministic generator code;
   they are not manual `.blend` edits.
7. A generated receipt records the configuration hash, athlete measurements, active expression,
   source-asset hashes (including the Faceunits pack manifest), presentation facts, and the hashes
   of exported artifacts.
8. Anatomical and visual acceptance are separate gates. Passing numeric limits does not make a
   pose coaching-approved.

## Testing layers

- `python -m unittest discover -s tests -v` runs portable host-side contracts on every push.
- `scripts/test-blender.ps1` runs the real Blender/MPFB generator with a temporary modified config
  and proves the receipt consumed that config.
- Human visual comparison remains mandatory for handedness, joint plausibility, and semantic
  fidelity to the drill reference.

## Extraction provenance

The initial implementation was extracted from
`braven-training/tools/movement_glb_mvp` on 2026-08-17. Future movement authoring changes belong in
this repository. Consumer-app integration should use exported, versioned artifacts rather than
copying authoring code back into the Flutter repository.
