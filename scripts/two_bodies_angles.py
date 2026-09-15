"""Do ANGLES cross between the two bodies where distances do not?

A distance measured on one body is not the same distance on another. An angle
may be. This measures the same angle, by the SAME formula, on both bodies: the
engine's solved skeleton and the rendered MPFB athlete.

Both trunks stand within 2.39 degrees of vertical on every phase, so world-down
is a fair reference for both, and 2.39 degrees is the error that choice admits.
"""
import json, sys, math
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
for extra in (REPO, REPO / "spikes"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))
import numpy as np
from export_blender_job import load_character, to_blender
from possession_solve import solve_movement
from archive_agreement import state_the_agreement

def archives() -> Path:
    for base in [Path(__file__).resolve()] + list(Path(__file__).resolve().parents):
        candidate = base / ".assets" / "archives"
        if candidate.is_dir():
            return candidate
    raise SystemExit("no .assets/archives found from this file")


A = archives() / "coach-figures-2413f9d"
DOWN = np.array([0.0, 0.0, -1.0])


def elevation(shoulder, elbow):
    """Degrees the upper arm is raised from hanging straight down."""
    v = np.asarray(elbow, dtype=float) - np.asarray(shoulder, dtype=float)
    n = np.linalg.norm(v)
    if n < 1e-9:
        return float("nan")
    return math.degrees(math.acos(max(-1.0, min(1.0, float(v @ DOWN) / n))))


def flexion(shoulder, elbow, wrist):
    """The angle at the elbow, three points."""
    a = np.asarray(shoulder, float) - np.asarray(elbow, float)
    b = np.asarray(wrist, float) - np.asarray(elbow, float)
    d = np.linalg.norm(a) * np.linalg.norm(b)
    if d < 1e-9:
        return float("nan")
    return math.degrees(math.acos(max(-1.0, min(1.0, float(a @ b) / d))))


state_the_agreement(A)

character = load_character()
rows = []
for path in sorted(A.glob("*.render.json")):
    receipt = json.loads(path.read_text(encoding="utf-8"))
    result = solve_movement(character, receipt["movementId"])
    index, points = result["index"], result["points"]
    drill = receipt["movementId"].replace("netball_", "")
    for phase in receipt["phases"]:
        frame = phase["frame"]
        if frame >= len(points):
            continue
        here = points[frame]
        def j(name):
            return to_blender(here[index[name]])
        for side in ("l", "r"):
            arm = phase["arms"][side]
            rows.append({
                "where": f"{drill}/{phase['name']} {side}",
                "elevEngine": elevation(j(f"{side}_uparm"), j(f"{side}_lowarm")),
                "elevRendered": elevation(arm["shoulder"], arm["elbow"]),
                "flexEngine": flexion(j(f"{side}_uparm"), j(f"{side}_lowarm"),
                                      j(f"{side}_wrist")),
                "flexRendered": flexion(arm["shoulder"], arm["elbow"], arm["wrist"]),
            })

for name, a, b in (("shoulder elevation", "elevEngine", "elevRendered"),
                   ("elbow flexion", "flexEngine", "flexRendered")):
    gaps = sorted(r[a] - r[b] for r in rows)
    worst = max(rows, key=lambda r: abs(r[a] - r[b]))
    print(f"{name}")
    print(f"  engine minus rendered: {gaps[0]:+7.2f} to {gaps[-1]:+7.2f} degrees, "
          f"median {gaps[len(gaps)//2]:+6.2f}")
    print(f"  worst: {worst['where']}  engine {worst[a]:.2f}  "
          f"rendered {worst[b]:.2f}")
    inside = sum(1 for r in rows if abs(r[a] - r[b]) <= 2.39)
    print(f"  within the 2.39 degree trunk allowance: {inside} of {len(rows)}")
    print()
print(f"{len(rows)} readings, build 2413f9d.")

print()
print("TRUNK LEAN, which sets the allowance above.")
rows2 = []
for path in sorted(A.glob("*.render.json")):
    receipt = json.loads(path.read_text(encoding="utf-8"))
    result = solve_movement(character, receipt["movementId"])
    index, points = result["index"], result["points"]
    for phase in receipt["phases"]:
        frame = phase["frame"]
        if frame >= len(points):
            continue
        here = points[frame]
        root = np.asarray(to_blender(here[index["root"]]))
        neck = np.asarray(to_blender(here[index["c_neck"]]))
        v = neck - root
        n = float(np.linalg.norm(v))
        if n < 1e-9:
            continue
        rows2.append(math.degrees(math.acos(max(-1.0, min(1.0, float(v[2]) / n)))))
print(f"  the engine's trunk leans {min(rows2):.2f} to {max(rows2):.2f} degrees "
      f"from vertical, over {len(rows2)} phases.")
print("  The renderer never rotates the spine: pose_stance translates the pelvis")
print("  and rotates the legs, pose_girdle rotates the clavicles. So the rendered")
print("  trunk stands at one angle always, and that costs at most the figure above.")
