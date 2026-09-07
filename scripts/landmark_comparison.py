"""Is the 2.5 cm fore-and-aft residual a landmark convention, or something real?

The pack carries a residual the shoulder fix does not remove: the engine's rest
shoulders sit -0.0648 torso lengths ahead of its root and this rig's sit
-0.0062. Two explanations predicted that single number equally well, so the
shoulders could never separate them:

  A  the engine's ROOT sits further back in the body than MPFB's PELVIS, in
     which case EVERY landmark differs by the same vector and the residual is a
     convention with nothing real in it.
  B  the bodies genuinely differ, and the figures inherit it.

A rigid shift of the origin moves every landmark by the SAME amount. So any
VARIATION in the per-landmark difference refutes A outright, and that argument
needs no correspondence between the two skeletons at all.

WHAT THE DATA CANNOT SEPARATE is posture from build. A different pose and a
differently proportioned body both produce varying differences. The vertical
column decides that question and it is reported separately below.

    python scripts/landmark_comparison.py
"""

from __future__ import annotations

# This rig, rest pose, torso lengths from the PELVIS. Divisor 42.7689 cm.
# Measured by `scripts/rest_landmarks.py`.
MINE = {
    "pelvis": (0.0000, 0.0000, 0.0000),
    "upperarm_l": (0.3522, 1.0000, -0.0062),
    "clavicle_l head": (0.0605, 1.0436, 0.0083),
    "spine_01": (0.0000, 0.1174, -0.0888),
    "spine_02": (0.0000, 0.2765, -0.0468),
    "spine_03": (0.0000, 0.4866, -0.0226),
    "neck_01": (0.0000, 1.1913, -0.0413),
    "head": (0.0000, 1.4395, 0.0322),
}

# The engine rig, rest pose, torso lengths from the ROOT. Divisor 49.6456 cm.
# The movement lane's dump, 2026-09-04. There is no scapula joint and one
# clavicle entry per side.
THEIRS = {
    "root": (0.0000, 0.0000, 0.0000),
    "l_uparm": (0.3542, 0.9979, -0.0648),
    "l_clavicle": (0.0568, 0.9699, 0.1280),
    "c_spine0": (0.0000, 0.0407, -0.0655),
    "c_spine1": (0.0000, 0.2631, -0.0433),
    "c_spine2": (0.0000, 0.4834, -0.0956),
    "c_spine3": (0.0000, 0.8547, -0.0748),
    "c_neck": (0.0000, 1.0432, 0.0138),
    "c_head": (0.0000, 1.2348, 0.0714),
    "c_head_null": (0.0000, 1.6190, 0.0714),
}

# Paired by ANATOMY, not by name. `spine_03` against `c_spine3` is the trap:
# see `spine_by_height` below.
PAIRS = [
    ("pelvis", "root"),
    ("upperarm_l", "l_uparm"),
    ("clavicle_l head", "l_clavicle"),
    ("neck_01", "c_neck"),
    ("head", "c_head"),
]

MY_TORSO_CM = 42.7689


def spine_by_height() -> None:
    """Pair the spine bones by HEIGHT, because the names do not correspond.

    Naming is not anatomy. `spine_03` sits at 0.4866 of this rig's torso and
    `c_spine3` at 0.8547 of the engine's. Pairing those two by their numbers
    would report a 0.3681 torso-length difference, which is 18.3 cm on the
    engine rig, and it would be reported as a posture finding. It is a naming
    coincidence.
    """
    print("SPINE CORRESPONDENCE BY HEIGHT, not by name")
    mine = [(name, value) for name, value in MINE.items()
            if name.startswith("spine")]
    theirs = [(name, value) for name, value in THEIRS.items()
              if name.startswith("c_spine")]
    for name, value in mine:
        nearest, other = min(
            ((other_name, other_value) for other_name, other_value in theirs),
            key=lambda row: abs(row[1][1] - value[1]))
        print(f"  {name:<12} up {value[1]:.4f}  ->  {nearest:<10} "
              f"up {other[1]:.4f}   apart {abs(other[1] - value[1]):.4f}")
    used = {min(theirs, key=lambda row: abs(row[1][1] - value[1]))[0]
            for _, value in mine}
    for name, value in theirs:
        if name not in used:
            print(f"  {'(none)':<12} {'':<12}  ->  {name:<10} "
                  f"up {value[1]:.4f}   NO COUNTERPART ON THIS RIG")
    trap = abs(THEIRS["c_spine3"][1] - MINE["spine_03"][1])
    print(f"  PAIRING BY NAME would report {trap:.4f} torso lengths between "
          f"spine_03 and c_spine3,")
    print(f"  which is {trap * MY_TORSO_CM:.1f} cm on this rig. It is a naming "
          f"coincidence and not a finding.")


def main() -> None:
    print(f"{'this rig':<18}{'the engine':<14}{'d across':>10}{'d up':>10}"
          f"{'d ahead':>10}")
    ahead, up = [], []
    for here, there in PAIRS:
        delta = [t - m for m, t in zip(MINE[here], THEIRS[there])]
        if here != "pelvis":
            ahead.append((delta[2], here))
            up.append((delta[1], here))
        print(f"{here:<18}{there:<14}{delta[0]:>10.4f}{delta[1]:>10.4f}"
              f"{delta[2]:>10.4f}")
    print()
    spread = max(v for v, _ in ahead) - min(v for v, _ in ahead)
    print("EXPLANATION A IS REFUTED, AND THE ARGUMENT NEEDS NO "
          "CORRESPONDENCE.")
    print("A rigid shift of the origin moves every landmark by the SAME "
          "vector. These")
    print(f"differ: the shoulders are {min(ahead)[0]:+.4f} and the clavicle "
          f"{max(ahead)[0]:+.4f}, a spread of")
    print(f"{spread:.4f} torso lengths, which is {spread * MY_TORSO_CM:.1f} cm "
          f"on this rig. Opposite signs cannot")
    print("come from a translation. The residual is real and no convention "
          "explains it away.")
    print()
    print("POSTURE OR BUILD IS NOT SETTLED, AND THE VERTICAL COLUMN IS WHY.")
    for value, name in up:
        print(f"  {name:<18}{value:>+9.4f}")
    print("The vertical difference GROWS with height, from the shoulders to "
          "the head. A pose")
    print("does not lengthen a neck. That pattern is a body PROPORTION "
          "difference, and a")
    print("proportion difference cannot be posed away. Calling the residual "
          "posture claims")
    print("more than this data holds, and it claims the more hopeful of the "
          "two.")
    print()
    spine_by_height()


if __name__ == "__main__":
    main()
