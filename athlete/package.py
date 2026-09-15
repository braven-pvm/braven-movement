"""Package the already-built studio, editable source and precise Tactics patch."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tactics', type=Path, required=True)
    args = parser.parse_args()
    output, tactics = args.output.resolve(), args.tactics.resolve()
    dist = HERE / 'viewer/dist'
    if not (dist / 'index.html').is_file():
        parser.error('Build athlete/viewer first with npm run build.')
    # Never package an old built asset alongside a newer root manifest.
    manifest = json.loads((output / 'manifest.json').read_text())
    expected = manifest['files']['netball-athlete.glb']['sha256']
    for asset in [output / 'netball-athlete.glb', dist / 'athlete-assets/netball-athlete.glb']:
        if hashlib.sha256(asset.read_bytes()).hexdigest() != expected:
            parser.error(f'Asset hash differs from the manifest: {asset}')
    shutil.copytree(dist, output / 'studio', dirs_exist_ok=True)
    if (output / 'athlete-in-motion.webm').is_file():
        shutil.copy2(output / 'athlete-in-motion.webm', output / 'studio/athlete-in-motion.webm')
    source = output / 'source'
    shutil.copytree(HERE, source / 'athlete', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('node_modules', 'dist', '__pycache__', '.vite'))
    (source / 'docs').mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE.parent / 'docs/NETBALL_ATHLETE_PIPELINE.md', source / 'docs/NETBALL_ATHLETE_PIPELINE.md')
    patch = subprocess.run(['git', '-C', str(tactics), 'diff', 'HEAD', '--binary', '--',
                            'src', 'tools/import-athlete.mjs', 'tools/athlete-browser.mjs', 'tools/athlete-passes-browser.mjs',
                            'tools/package-athlete.mjs', 'tools/athlete-package-browser.mjs', 'tools/Open-Braven-Tactics.ps1',
                            'package.json', 'vite.config.ts', '.env.athlete',
                            'docs/athlete-local-build.md', '.gitignore'],
                           check=True, capture_output=True).stdout
    if b'authored-athlete.test.ts' not in patch:
        parser.error('Stage the new Tactics regression-test file before packaging the patch.')
    (source / 'tactics-authored-athlete.patch').write_bytes(patch)
    for name in ['serve.py', 'Open-Athlete-Studio.ps1']:
        shutil.copy2(HERE / name, output / name)
    if (HERE / 'VALIDATION.md').is_file():
        shutil.copy2(HERE / 'VALIDATION.md', output / 'VALIDATION.md')
    receipt = {
        'assetSha256': expected,
        'modelRevision': manifest.get('revision', 1),
        'movementBase': subprocess.check_output(['git', '-C', str(HERE), 'rev-parse', 'HEAD'], text=True).strip(),
        'tacticsBase': subprocess.check_output(['git', '-C', str(tactics), 'rev-parse', 'HEAD'], text=True).strip(),
        'tacticsPatchSha256': hashlib.sha256(patch).hexdigest(),
        'movementSourceCommit': manifest.get('movementSourceCommit'),
        'movementLibrary': 'movement-library/manifest.json',
        'studioScriptSha256': {str(path.relative_to(dist)).replace('\\', '/'):
                              hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in sorted((dist / 'assets').glob('*.js'))},
        'offlineStudio': 'studio/index.html',
        'launcher': 'Open-Athlete-Studio.ps1',
    }
    (output / 'package-receipt.json').write_text(json.dumps(receipt, indent=2))
    (output / 'README.md').write_text('''# Braven netball athlete

Run **Open-Athlete-Studio.ps1** to open the working animated model at http://127.0.0.1:5393/.
Python is required to serve the local files. Blender, Node and the internet are not required to use the packaged studio.

Choose a catch, pass, deflection or landing from Animation library. Use the named phase buttons to pause at contact, release or pull-in, and turn Repeat motion off for a single play. Switch Kit between skirt/shorts, or open Pose to edit any of 70 controls, including the ball.
Movement source > Braven Tactics uses the real bundled Tactics pose engine.

The studio opens on Jump & reach. Its flight, Jump catch & pull in and Double-foot landing have revised gravity and landing timing. Play at 1x to inspect the corrected movement; the animation keys remain editable.

- **netball-athlete.blend** — editable model, garments, 70 deformation bones, 4 IK targets and 17 animations.
- **athlete-source.blend** — original human with editable phenotype shape keys.
- **netball-athlete.glb** — portable animated runtime model.
- **athlete-in-motion.webm** — recording of the actual model moving in WebGL.
- **movement-library/** — pinned Braven Movement source snapshot, full solved motion jobs and source hashes. Re-baking these jobs in Blender needs no MHR runtime.
- **movement-library.json** — technique phases, source review status and retarget measurements.
- [Detailed use, Blender editing, rebuilding, limitations and Tactics integration](source/athlete/README.md).
- [Blender / Unity / UE5 / Three.js / Python and other options](source/docs/NETBALL_ATHLETE_PIPELINE.md).
- [Validation summary](VALIDATION.md), JSON verification reports and screenshots in verification/.

Twelve techniques come from Braven Movement; five general clips are retained. Seven imported techniques pass their source checkpoints; five are grouped under needs review. Coaching approval of the retargeted athlete is pending. The full local Tactics build now samples the native rig on its timeline and aligns its match ball to the imported hand contacts. Run **Open-Braven-Tactics.ps1** for the packaged build at http://127.0.0.1:5396/, or use the development server at http://127.0.0.1:5395/. See **TACTICS-LOCAL-BUILD.md** for controls, scope and rebuilding. Skirt deformation uses bones rather than physical cloth collision.
''', encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
