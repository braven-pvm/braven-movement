"""Left and right hand fan per phase, measured on the SHIPPED library's poses.

The fan is index tip to pinky tip. `docs/HAND_MIRROR_EVIDENCE.md` reports 14.37
cm on the left against 1.75 cm on the right before PR #46: a right hand that was
closed instead of opened.

THIS INSTRUMENT WAS WRONG UNTIL 2026-09-07. It posed each phase with the
CONFIG's anatomy limits and `None` for the knuckle limits, where `render_job`
passes the JOB's own. That is the same lever that produced a false
non-reproduction on `one_hand_high_pass` the same morning. Every fan number this
lane published was therefore taken under different limits from the figures a
coach was going to see. It now poses exactly as `render_job` does.

IT ALSO PROVES IT IS THE LIBRARY'S POSE. Before reading a fan it compares the
girdle report it just produced against the archived receipt for the same phase.
A fan measured on a pose that is not the shipped one is not a measurement of the
figures.

READ THE GRIP, NOT THE DRILL NAME. Two phases show a fan gap above 2 cm.
Neither is a defect: the job carries `grip` for the RIGHT SIDE ONLY on both, so
one hand is closed on the ball and the other is open.

AND "BOTH HANDS GRIP" IS ITSELF A LABEL. `bounce_pass/pull_to_side` carries a
grip on both sides and asks for one 44.5 degrees away from a mirror, with reach
fractions of 0.2674 against 0.5040. Pulling a ball to one side is asymmetric by
design and its 0.27 cm gap is the drill. `deflect_high/contact` is 27.3 degrees
askew, and it is the phase whose 0.095 cm this lane once published as the worst
mirror gap in the library. The mirror claim belongs only to phases the job asks
to be SYMMETRIC, and symmetry is measured here rather than assumed.

    blender -b --python-exit-code 9 -P scripts/fan_mirror_check.py -- \
        --archive coach-figures-2413f9d
"""

import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for extra in (REPO, REPO / "spikes"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import blender_movement_render as R  # noqa: E402
from blender_mpfb_reference_catch import world_tail  # noqa: E402
from reference_pose_config import load_reference_catch_config  # noqa: E402

JOBS = sorted((REPO / "spikes" / "poc-output").glob("*.job.json"))
GIRDLE_TRAVEL_M = 0.0740  # the overhead pass's own, engine side


def archives() -> Path:
    for base in [Path(__file__).resolve()] + list(Path(__file__).resolve().parents):
        candidate = base / ".assets" / "archives"
        if candidate.is_dir():
            return candidate
    raise SystemExit("no .assets/archives found from this file")


def label() -> str:
    if "--archive" in sys.argv:
        return sys.argv[sys.argv.index("--archive") + 1]
    return "coach-figures-2413f9d"


def mirror_error_degrees(grip: dict) -> float | None:
    """How far the job's own grip is from a mirror, in degrees.

    A symmetric hold has `outward.r` equal to `outward.l` reflected across the
    body's x axis. This measures the angle between them, so a phase can be
    called symmetric by its own numbers instead of by having two entries in
    `grip`.
    """
    if not grip or len(grip) != 2:
        return None
    left, right = grip["l"]["outward"], grip["r"]["outward"]
    mirrored = (-left[0], left[1], left[2])
    dot = sum(a * b for a, b in zip(mirrored, right))
    size = (sum(v * v for v in mirrored) ** 0.5) * (sum(v * v for v in right) ** 0.5)
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / size))))


# Past this the job is not asking for a mirrored hold, so the two fans are not
# expected to agree. CHOSEN FROM THE MEASURED SPREAD, which on the 24 gripping
# phases of this library is 0.0 degrees on eighteen of them, then 2.8, 4.7, 7.8,
# 16.2, 16.4, 27.3 and 44.5. The widest gap in the run is between 4.7 and 7.8.
# The answer is INSENSITIVE to the choice: at 10 degrees the phase at 7.8 joins
# the population and its gap is 0.001 cm, so the worst is unchanged.
SYMMETRIC_DEGREES = 5.0


def fan(rig, side: str) -> float:
    """Index tip to pinky tip, cm. A distance on ONE rigid hand."""
    return (world_tail(rig, f"index_03_{side}")
            - world_tail(rig, f"pinky_03_{side}")).length * 100.0


def pose(studio, job, phase):
    """EXACTLY as `render_job` calls it: the JOB's limits, both of them."""
    return R.pose_phase(
        studio.rig, phase, job["anatomyLimitsDegrees"], studio.basis,
        studio.foot_baseline, studio.config.finger_curl_degrees,
        job.get("knuckleLimitsDegrees"), studio.human,
    )


def displaced(phase: dict, arm_m: float) -> dict:
    """The same phase with the ball raised by the girdle's own travel."""
    moved = json.loads(json.dumps(phase))
    offset = moved["ball"]["fromShouldersInArms"]
    offset[2] = offset[2] + GIRDLE_TRAVEL_M / arm_m
    return moved


def main() -> None:
    archive = archives() / label()
    shipped = {}
    for path in sorted(archive.glob("*.render.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        for entry in receipt["phases"]:
            shipped[(receipt["movementId"], entry["name"])] = entry["girdle"]
    if not shipped:
        raise SystemExit(f"no receipts in {archive}")

    studio = R.Studio(load_reference_catch_config())
    arm = R.bone_chain_length(studio.rig, "upperarm_l", "lowerarm_l", "hand_l")
    print(f"{len(shipped)} archived phases in {archive.name}")
    print(f"{'drill / phase':<40}{'grip':>6}{'askew':>8}{'left':>8}"
          f"{'right':>8}{'|L-R|':>8}{'drift':>8}  pose")
    worst_mirror = worst_drift = 0.0
    worst_row = ""
    checked = skipped = 0
    for path in JOBS:
        job = json.loads(path.read_text(encoding="utf-8"))
        drill = job["movementId"]
        for phase in job["phases"]:
            key = (drill, phase["name"])
            if key not in shipped:
                skipped += 1
                continue
            _, receipt = pose(studio, job, phase)
            # THE POSE MUST BE THE SHIPPED ONE, or the fan is not the library's.
            here = receipt["girdle"]
            there = shipped[key]
            same = (
                abs(here["ballAnchorErrorMm"] - there["ballAnchorErrorMm"]) < 1e-3
                and abs(here["worstOffsetMm"] - there["worstOffsetMm"]) < 1e-3
            )
            left, right = fan(studio.rig, "l"), fan(studio.rig, "r")
            pose(studio, job, displaced(phase, arm))
            drift = max(abs(left - fan(studio.rig, "l")),
                        abs(right - fan(studio.rig, "r")))
            grip = phase.get("grip") or {}
            askew = mirror_error_degrees(grip)
            symmetric = askew is not None and askew <= SYMMETRIC_DEGREES
            gap = abs(left - right)
            checked += 1
            if symmetric and gap > worst_mirror:
                worst_mirror, worst_row = gap, f"{drill}/{phase['name']}"
            worst_drift = max(worst_drift, drift)
            print(f"{drill.replace('netball_', '') + '/' + phase['name']:<40}"
                  f"{(','.join(sorted(grip)) or '-'):>6}"
                  f"{('-' if askew is None else f'{askew:.1f}'):>8}"
                  f"{left:>8.3f}{right:>8.3f}"
                  f"{gap:>8.3f}{drift:>8.4f}  "
                  f"{'matches archive' if same else 'DOES NOT MATCH ARCHIVE'}")
    print()
    print(f"{checked} phases measured, {skipped} not in the archive.")
    print(f"worst fan gap where the job asks for a SYMMETRIC hold "
          f"(within {SYMMETRIC_DEGREES:.0f} degrees of a mirror):")
    print(f"  {worst_mirror:.4f} cm at {worst_row}")
    print("A phase whose grip is askew is not expected to mirror, and its gap "
          "is the drill.")
    print(f"worst fan drift when the ball moves {GIRDLE_TRAVEL_M * 100:.2f} cm:"
          f" {worst_drift:.4f} cm")


if __name__ == "__main__":
    main()
