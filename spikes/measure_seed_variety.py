"""Measure the cold-start seed set that was built, measured and not adopted.

`seeds()` yields four candidates that differ only in `{side}_lowarm_twist`.
That parameter sits BELOW the elbow: across every seed value the elbow moves
0.000 cm and the wrist moves 0.000 cm. The four candidates are identical from
the shoulder to the wrist and differ only in how the hand is rotated about the
forearm, so the cold start has never been able to choose which side the elbow
goes. `{side}_uparm_twist`, at the shoulder, does select it — the same values
move the wrist by up to 44 cm.

That was found while chasing a 19.3 degree single-frame step, and it is real.
It was also not the cause. The cause was a waiting point measured from the
shoulder midpoint and spent as a per-hand reach, and once that was corrected
the richer seed set changed almost nothing.

This script exists so that "almost nothing" is a number anyone can reproduce
rather than a claim in a merged pull request. It applies the alternative
generator in memory, without editing any source file, and prints both states
side by side.

    pixi run seeds

Nothing here is imported by the engine. If the evidence ever changes — a new
drill, a new cold-start pathology — this is the switch, already measured.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

import contact_solve  # noqa: E402
from ball_track import has_ball  # noqa: E402
from contact_solve import TWIST_SEEDS  # noqa: E402
from movement_engine import library, load_character  # noqa: E402
from technique import has_technique, load_technique, technique_path  # noqa: E402

THRESHOLDS = (5.0, 10.0, 15.0, 20.0, 30.0)


def uparm_seeds(character, rest: np.ndarray, start: np.ndarray | None):
    """The alternative: the forearm seeds, plus per-side humeral twist.

    Per side rather than together, because the fault it was written for was ONE
    arm. A seed that twists both the same way scores badly on whichever arm did
    not need it.

    The forearm seeds are kept rather than replaced. They rotate the hand,
    which the grip constraints do see, and whether they earn their own place is
    a separate question this script does not ask.
    """
    if start is not None:
        yield np.asarray(start, dtype=np.float32)
    names = list(character.parameter_transform.names)

    def index_of(name: str) -> int | None:
        return names.index(name) if name in names else None

    lower = [index_of(f"{side}_lowarm_twist") for side in ("l", "r")]
    upper = [index_of(f"{side}_uparm_twist") for side in ("l", "r")]

    for value in TWIST_SEEDS:
        seed = rest.copy()
        for number in lower:
            if number is not None:
                seed[number] = value
        yield seed

    if any(number is None for number in upper):
        return
    for left in TWIST_SEEDS:
        for right in TWIST_SEEDS:
            seed = rest.copy()
            seed[upper[0]] = left
            seed[upper[1]] = right
            yield seed


def drills() -> list[str]:
    return [
        name
        for name in sorted(library())
        if has_ball(name)
        and has_technique(name)
        and load_technique(technique_path(name)).possession_ready
    ]


def measure(character) -> dict:
    """Solve the library and return the two tables the packs are judged on."""
    from possession_solve import solve_movement

    index = {
        name: number for number, name in enumerate(character.skeleton.joint_names)
    }
    counts = {threshold: 0 for threshold in THRESHOLDS}
    contacts, worst = [], 0.0
    started = time.perf_counter()
    for movement_id in drills():
        result = solve_movement(character, movement_id)
        points = result["points"]
        contact = result["possession"].contact_frame
        contacts.append(
            float(
                np.linalg.norm(
                    points[contact][index["l_lowarm"]]
                    - points[contact][index["r_lowarm"]]
                )
            )
        )
        for side in ("l", "r"):
            for parent, child in (("uparm", "lowarm"), ("lowarm", "wrist")):
                along = []
                for frame in points:
                    line = frame[index[f"{side}_{child}"]] - frame[index[f"{side}_{parent}"]]
                    along.append(line / np.linalg.norm(line))
                for number in range(1, len(along)):
                    step = float(
                        np.degrees(
                            np.arccos(
                                np.clip(np.dot(along[number], along[number - 1]), -1, 1)
                            )
                        )
                    )
                    worst = max(worst, step)
                    for threshold in THRESHOLDS:
                        if step > threshold:
                            counts[threshold] += 1
    return {
        "counts": counts,
        "contactMean": sum(contacts) / len(contacts),
        "worstStep": worst,
        "seconds": time.perf_counter() - started,
    }


def main(argv: list[str]) -> int:
    character = load_character()
    rest = np.zeros(character.parameter_transform.size, dtype=np.float32)
    shipped = sum(1 for _ in contact_solve.seeds(character, rest, None))
    offered = sum(1 for _ in uparm_seeds(character, rest, None))

    print(f"the shipped seed set has {shipped} candidates")
    print(f"the alternative has {offered}\n")

    print("what the shipped seeds can move, on a bent left arm:")
    names = list(character.parameter_transform.names)
    index = {
        name: number for number, name in enumerate(character.skeleton.joint_names)
    }
    from movement_engine import joint_positions

    base = rest.copy()
    base[names.index("l_elbow_bend")] = 1.2
    settled = joint_positions(character, base)
    for parameter in ("l_lowarm_twist", "l_uparm_twist"):
        number = names.index(parameter)
        moves = []
        for value in TWIST_SEEDS:
            seed = base.copy()
            seed[number] = value
            posed = joint_positions(character, seed)
            moves.append(
                (
                    float(np.linalg.norm(posed[index["l_lowarm"]] - settled[index["l_lowarm"]])),
                    float(np.linalg.norm(posed[index["l_wrist"]] - settled[index["l_wrist"]])),
                )
            )
        print(
            f"  {parameter:16s} elbow moves at most {max(m[0] for m in moves):6.3f} cm, "
            f"wrist at most {max(m[1] for m in moves):7.3f} cm"
        )
    print(
        "\nA parameter that cannot move the elbow cannot choose which side it\n"
        "goes on, which is the only thing the cold start needed to decide.\n"
    )

    print("solving the library with the shipped seeds ...")
    before = measure(character)
    contact_solve.seeds = uparm_seeds
    print("solving the library with the alternative ...")
    after = measure(character)

    print(f"\n{'':16s} " + " ".join(f">{t:.0f}deg".rjust(7) for t in THRESHOLDS)
          + f" {'worst':>7s} {'contact':>8s} {'seconds':>8s}")
    for name, found in (("shipped", before), ("alternative", after)):
        print(
            f"{name:16s} "
            + " ".join(f"{found['counts'][t]:7d}" for t in THRESHOLDS)
            + f" {found['worstStep']:7.1f} {found['contactMean']:8.2f}"
            f" {found['seconds']:8.1f}"
        )
    print(
        "\nThe alternative was dropped for moving the tables this much at this\n"
        "cost. Reproduce it before turning it on, and record what changed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
