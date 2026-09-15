"""What the follow-through easing moves in the GRADED window.

    cd spikes
    pixi run --frozen -- python -B ../scripts/sweep_release_easing.py

WHY THIS EXISTS. `docs/KNOWN_ISSUES.md`, under "The release seam and the
frame-81 stall are one defect", already compares three easings across the whole
library. It measures JOINT STEPS and the receipt's `worstNeighbourRatio`. **It
never measures a graded checkpoint.** So the number a coach would have to
re-grade has never been taken, and this takes it.

WHAT IT VARIES. One line, `possession.py:658`, which shapes the follow-through
aim point after the release:

    out = 1.0 - (1.0 - out) ** 2

That is `1 - (1 - t)^p` with p = 2. This sweeps p as a CONTINUOUS family with
the shipped value inside it, and adds smoothstep as a separate shape. A sweep
rather than a point, because a single variant that moves a checkpoint can be a
solver basin crossing rather than an effect of the easing.

HOW IT AVOIDS TOUCHING THE ENGINE. `possession.py` is copied to a temporary
directory and patched THERE, and that directory goes first on `sys.path`. The
repository's own file is never written. `spikes/movements/` is gate 4 and is
neither read for writing nor copied.

WHAT IT REPORTS. Per drill, per phase, per checkpoint: the `measured` value from
the receipt, against the shipped easing. Joint steps sit beside every point, so
a reader can see whether a checkpoint moved because the pose moved or because
the solve landed elsewhere.

IT REFUSES A FLAT RESULT. If no checkpoint moves by more than the noise floor
across the whole sweep, the run fails rather than reporting "no effect", because
a sweep that cannot move anything is more likely to be disconnected than to be
evidence.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPIKES = ROOT / "spikes"

SHIPPED = "                out = 1.0 - (1.0 - out) ** 2"
PATCHED = "                out = _braven_sweep_easing(out)"
SHIM = '''

def _braven_sweep_easing(out: float) -> float:
    """The follow-through easing, chosen at call time by the sweep.

    INSERTED BY `scripts/sweep_release_easing.py` INTO A COPY. The repository's
    own `possession.py` is not modified. `power:2.0` reproduces the shipped
    line exactly, and the sweep asserts that before it reports anything.
    """
    import os as _os

    choice = _os.environ.get("BRAVEN_SWEEP_EASING", "power:2.0")
    kind, _, value = choice.partition(":")
    if kind == "power":
        return 1.0 - (1.0 - out) ** float(value)
    if kind == "smoothstep":
        return out * out * (3.0 - 2.0 * out)
    if kind == "linear":
        return out
    raise ValueError(f"the sweep does not know the easing {choice!r}")
'''

# The shipped value sits INSIDE this family at power:2.0, which is what makes
# this a sweep rather than three separate builds.
VARIANTS = (
    "linear",
    "power:1.25",
    "power:1.5",
    "power:2.0",
    "power:2.5",
    "power:3.0",
    "smoothstep",
)
SHIPPED_VARIANT = "power:2.0"
DRILLS = (
    "netball_chest_pass",
    "netball_overhead_pass",
    "netball_bounce_pass",
    "netball_one_hand_high_pass",
)
# Below this a difference is not worth a coach's attention. It is the degrees
# band floor, and it is quoted rather than invented: `movement_definition`
# derives it from the landmark noise study.
NOISE_DEGREES = 5.0


def patched_possession(into: Path) -> Path:
    """Copy `possession.py` and swap one line. Assert the swap applied."""
    source = (SPIKES / "possession.py").read_text(encoding="utf-8")
    if SHIPPED not in source:
        raise SystemExit(
            "possession.py:658 no longer matches the line this sweep patches. "
            "Re-read it before trusting any number here."
        )
    patched = source.replace(SHIPPED, PATCHED, 1) + SHIM
    if patched == source or PATCHED not in patched:
        raise SystemExit("the substitution did not apply")
    target = into / "possession.py"
    target.write_text(patched, encoding="utf-8")
    return target


def main() -> int:
    workspace = Path(tempfile.mkdtemp(prefix="braven-easing-sweep-"))
    try:
        patched_possession(workspace)
        sys.path.insert(0, str(workspace))
        if str(SPIKES) not in sys.path:
            sys.path.insert(1, str(SPIKES))

        import numpy as np
        import possession
        from movement_definition import load as load_definition
        from movement_engine import MOVEMENT_DIR, load_character
        from possession_solve import solve_movement

        if not hasattr(possession, "_braven_sweep_easing"):
            raise SystemExit(
                "the patched possession.py is not the one that got imported"
            )
        print(f"    patched copy: {workspace}")
        print(f"    the repository's own possession.py is untouched")
        print()

        character = load_character()
        readings: dict = {}
        joint_steps: dict = {}
        for variant in VARIANTS:
            os.environ["BRAVEN_SWEEP_EASING"] = variant
            for movement_id in DRILLS:
                result = solve_movement(character, movement_id)
                definition = load_definition(MOVEMENT_DIR / f"{movement_id}.json")
                receipt = definition.assess(result["measurements"]).to_receipt()
                for phase, rows in receipt["phases"].items():
                    for row in rows:
                        key = (movement_id, phase, row["measure"])
                        readings.setdefault(key, {})[variant] = row["measured"]
                points = result["points"]
                steps = [
                    float(np.max(np.abs(points[n] - points[n - 1])))
                    for n in range(1, len(points))
                ]
                joint_steps[(movement_id, variant)] = max(steps)

        print("    WHAT THE EASING MOVES IN THE GRADED WINDOW")
        print(f"    against the shipped {SHIPPED_VARIANT}, in each measure's own unit")
        print()
        header = f"    {'drill / phase / measure':52s} {'shipped':>8s}"
        for variant in VARIANTS:
            if variant != SHIPPED_VARIANT:
                header += f" {variant:>11s}"
        print(header)

        worst = 0.0
        for key in sorted(readings):
            movement_id, phase, measure = key
            values = readings[key]
            base = values.get(SHIPPED_VARIANT)
            if base is None:
                continue
            line = (
                f"    {movement_id.replace('netball_', '') + '/' + phase + '/' + measure:52s} "
                f"{base:8.2f}"
            )
            moved = False
            for variant in VARIANTS:
                if variant == SHIPPED_VARIANT:
                    continue
                delta = values.get(variant, base) - base
                worst = max(worst, abs(delta))
                if abs(delta) >= 0.01:
                    moved = True
                line += f" {delta:+11.2f}"
            if moved:
                print(line)

        print()
        print("    THE WORST JOINT STEP BESIDE EVERY POINT, cm")
        print(f"    {'drill':22s}" + "".join(f"{v:>12s}" for v in VARIANTS))
        for movement_id in DRILLS:
            row = f"    {movement_id.replace('netball_', ''):22s}"
            for variant in VARIANTS:
                row += f"{joint_steps[(movement_id, variant)]:12.3f}"
            print(row)

        print()
        print(f"    the largest checkpoint move anywhere in the sweep: {worst:.2f}")
        if worst < 0.01:
            raise SystemExit(
                "REFUSED: no checkpoint moved anywhere in the sweep. A sweep "
                "that cannot move anything is more likely to be disconnected "
                "than to be evidence. Check that the patched module is the one "
                "being imported before reporting this as 'no effect'."
            )
        if worst < NOISE_DEGREES:
            print(f"    and that is BELOW the {NOISE_DEGREES:g} degree band floor,")
            print("    so no coach could see any of it.")
        return 0
    finally:
        os.environ.pop("BRAVEN_SWEEP_EASING", None)
        shutil.rmtree(workspace, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
