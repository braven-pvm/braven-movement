# Movement GLB MVP

This engineering spike proves the internal authoring boundary:

```text
Cascadeur GUI -> animated GLB -> versioned job -> headless Blender -> transparent PNG + hash receipt
```

It does **not** make the bundled Cascadeur sample figure publishable, provide a coaching-approved
pose, or integrate media into the Braven reader.

## Verified on 2026-08-16

- Cascadeur `2026.2`, local script server `0.3.1`.
- The installed free licence blocks FBX (`is_export_available() == false`) but permits animated GLB.
- Live `Cascy.casc` export: 2,904,324 bytes, 67 nodes, 1 animation, 198 channels.
- Blender `4.5.12 LTS` in background mode.
- Corrected engine probe: Cycles PASS and EEVEE PASS, both RGBA with `max_alpha=1.000`.
- Real render: 1080 x 1350 EEVEE PNG, 706,229 bytes, 214,946 non-transparent pixels.
- The job and render receipts independently matched the GLB and PNG SHA-256 hashes.

The visual result is a complete teal Cascy figure on transparent background. Cascy is a stylised
cat and is only a mechanism proof, not an athlete, a netball movement, or a distributable asset.

## Files

| File | Responsibility |
|---|---|
| `movement_contract.py` | Inspect GLB animation bytes, publish/read the job contract, verify image alpha, calculate normalisation. |
| `cascadeur_glb_export.py` | Ask the live Cascadeur script server for an animated GLB and publish `job.json` only after inspecting it. |
| `blender_probe.py` | Render a real RGBA cube with Cycles and EEVEE and verify pixels without slicing Blender's `bpy_prop_array`. |
| `blender_glb_render.py` | Import the job's GLB, normalise the figure to 1.75 m, apply the MVP look, render one frame, and write a hash receipt. |

## Run

In Cascadeur, open a **working copy** of the scene and select
`Scripts -> MCP -> Start script server`. Leave the application idle during export.

From the repository worktree:

```powershell
$output = Join-Path $env:TEMP 'braven_movement_glb_mvp'

python tools\movement_glb_mvp\cascadeur_glb_export.py `
  --movement-id cascy_internal_probe `
  --fps 30.0 `
  --output $output

& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' `
  -b --factory-startup --python-exit-code 9 `
  -P tools\movement_glb_mvp\blender_glb_render.py -- `
  --job (Join-Path $output 'job.json') `
  --output (Join-Path $output 'cascy.png') `
  --frame 0
```

`30.0` above is an **unconfirmed internal-test assertion**. For authored content, read the scene's
FPS in Cascadeur's UI and pass that exact value. Cascadeur exposes no FPS getter.

## Next coaching sample

1. Copy a suitable human sample or licensed athletic figure out of `Program Files`; never author in
   the installed sample.
2. Open the copy in Cascadeur and confirm its displayed FPS.
3. Make one pose only: the first-contact/take frame of the two-handed catch, with a correctly sized
   ball. Do not attempt the full phase sequence yet.
4. Have the coaching owner confirm the movement meaning and pose before styling it further.
5. Re-run the same exporter and renderer with a new movement id and the confirmed FPS.

The bundled `UE5_Quinn.casc` sample is technically useful because it has articulated hands and
clavicles, but its commercial publication rights are unresolved. Any Quinn render remains
internal-only until Braven has a written licence answer or supplies a licensed figure.
