"""Left and right hand fan per phase, measured on the SHIPPED library's poses.

The fan is index tip to pinky tip. `docs/HAND_MIRROR_EVIDENCE.md` reports 14.37
cm on the left against 1.75 cm on the right before PR #46: a right hand that was
closed instead of opened.

A LATENT FAULT, FIXED, THAT CHANGED NO NUMBER HERE. This instrument posed with
the CONFIG's anatomy limits and `None` for the knuckle limits, where
`render_job` passes the JOB's own. It now poses as `render_job` does. Posing all
48 shipped phases BOTH ways gives a largest fan difference of 0.000000 cm,
because all twelve jobs carry anatomy limits identical to the config and no
knuckle reaches its licence on these phases. So no published fan number moved
because of it. The fault is real and would bite the first job whose limits
differ from the config, which is why it is fixed, and it is NOT the reason the
published gap changed.

WHAT THE GATING CHECK PINS, AND WHAT IT DOES NOT. `pose_girdle` runs before the
limits, the ball, the arms and the hands are touched, so a girdle comparison
alone cannot see a change to any of them. This compares three things and RAISES
on any mismatch:

  the job's sha256 against the receipt's `jobSha256`   pins the INPUTS
  `girdle.ballAnchorErrorMm` and `worstOffsetMm`       pins the girdle
  each hand's wrist bend, forearm roll and palm error  pins the HANDS

The third is the one a fan claim needs, and it was absent: a girdle check reads
`same` with the forearm roll cut from 75 degrees to 15 and the fans moved by 2.15
cm. It still does not pin everything a picture contains. It pins the inputs, the
girdle and the hands.

READ THE GRIP, NOT THE DRILL NAME. Two phases show a fan gap above 2 cm. Neither
is a defect: the job carries `grip` for the RIGHT SIDE ONLY on both, so one hand
is closed on the ball and the other is open.

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

import hashlib
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

# Past this the job is not asking for a mirrored hold, so the two fans are not
# expected to agree. CHOSEN FROM THE MEASURED SPREAD, which on the 25 gripping
# phases of this library is 0.0 degrees on eighteen of them, then 2.8, 4.7, 7.8,
# 16.2, 16.4, 27.3 and 44.5. The widest gap in that run is 27.3 to 44.5; the
# widest below 10 degrees is 4.7 to 7.8.
# THE ANSWER IS INSENSITIVE TO THE CHOICE over a wide range: raising the
# threshold to 20 degrees admits the phases at 7.8, 16.2 and 16.4, whose gaps
# are 0.001, 0.037 and 0.017 cm, so the worst is unchanged. It BREAKS at 30,
# which admits `deflect_high/contact` at 27.3 degrees and 0.085 cm.
SYMMETRIC_DEGREES = 5.0


def archives() -> Path:
    """Find `.assets/archives`, or say plainly that it is not here.

    The archives sit beside the main checkout and are not in the repository, so
    a fresh clone does not have them. Failing with the reason beats failing with
    an empty glob.
    """
    for base in [Path(__file__).resolve()] + list(Path(__file__).resolve().parents):
        candidate = base / ".assets" / "archives"
        if candidate.is_dir():
            return candidate
    raise SystemExit(
        "no .assets/archives found from this file. The archives are not in the "
        "repository; they sit beside the main checkout. Pass --archives <path> "
        "to name one."
    )


def option(flag: str, fallback: str) -> str:
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else fallback


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


def refuse_unless_shipped(label: str, here: dict, there: dict) -> None:
    """RAISE unless this pose reproduces the archived one.

    A gate that only decorates a printed row is not a gate: the run would exit 0
    with every row marked as a mismatch. This stops.
    """
    girdle, was = here["girdle"], there["girdle"]
    for field in ("ballAnchorErrorMm", "worstOffsetMm"):
        if abs(girdle[field] - was[field]) > 1e-3:
            raise SystemExit(
                f"{label}: girdle {field} is {girdle[field]} here and "
                f"{was[field]} in the archive. This is not the shipped pose."
            )
    for side in ("l", "r"):
        for field in ("wristBendDegrees", "forearmRollDegrees",
                      "palmNormalErrorDegrees"):
            mine = here["hands"][side][field]
            theirs = there["hands"][side][field]
            if abs(mine - theirs) > 1e-2:
                raise SystemExit(
                    f"{label}: hand {side} {field} is {mine} here and "
                    f"{theirs} in the archive. This is not the shipped pose, "
                    f"and a fan read from it is not the library's."
                )


def displaced(phase: dict, arm_m: float) -> dict:
    """The same phase with the ball raised by the girdle's own travel."""
    moved = json.loads(json.dumps(phase))
    offset = moved["ball"]["fromShouldersInArms"]
    offset[2] = offset[2] + GIRDLE_TRAVEL_M / arm_m
    return moved


def main() -> None:
    root = Path(option("--archives", str(archives())))
    archive = root / option("--archive", "coach-figures-2413f9d")
    shipped, digests = {}, {}
    for path in sorted(archive.glob("*.render.json")):
        receipt = json.loads(path.read_text(encoding="utf-8"))
        digests[receipt["movementId"]] = receipt.get("jobSha256")
        for entry in receipt["phases"]:
            shipped[(receipt["movementId"], entry["name"])] = entry
    if not shipped:
        raise SystemExit(f"no receipts in {archive}")

    studio = R.Studio(load_reference_catch_config())
    arm = R.bone_chain_length(studio.rig, "upperarm_l", "lowerarm_l", "hand_l")
    print(f"{len(shipped)} archived phases in {archive.name}")
    print(f"{'drill / phase':<40}{'grip':>6}{'askew':>8}{'left':>8}"
          f"{'right':>8}{'|L-R|':>8}{'drift':>8}")
    worst_mirror = worst_drift = 0.0
    mirror_row = drift_row = ""
    checked = skipped = gripping = 0
    for path in JOBS:
        job = json.loads(path.read_text(encoding="utf-8"))
        drill = job["movementId"]
        if drill in digests and digests[drill]:
            here = hashlib.sha256(path.read_bytes()).hexdigest()
            if not here.startswith(digests[drill]):
                raise SystemExit(
                    f"{drill}: this job file is {here[:16]} and the archive was "
                    f"rendered from {digests[drill]}. The inputs differ."
                )
        for phase in job["phases"]:
            key = (drill, phase["name"])
            if key not in shipped:
                skipped += 1
                continue
            _, receipt = pose(studio, job, phase)
            refuse_unless_shipped(f"{drill}/{phase['name']}", receipt,
                                  shipped[key])
            left, right = fan(studio.rig, "l"), fan(studio.rig, "r")
            pose(studio, job, displaced(phase, arm))
            drift = max(abs(left - fan(studio.rig, "l")),
                        abs(right - fan(studio.rig, "r")))
            grip = phase.get("grip") or {}
            askew = mirror_error_degrees(grip)
            symmetric = askew is not None and askew <= SYMMETRIC_DEGREES
            gap = abs(left - right)
            checked += 1
            gripping += 1 if askew is not None else 0
            if symmetric:
                if gap > worst_mirror:
                    worst_mirror, mirror_row = gap, f"{drill}/{phase['name']}"
                if drift > worst_drift:
                    worst_drift, drift_row = drift, f"{drill}/{phase['name']}"
            print(f"{drill.replace('netball_', '') + '/' + phase['name']:<40}"
                  f"{(','.join(sorted(grip)) or '-'):>6}"
                  f"{('-' if askew is None else f'{askew:.1f}'):>8}"
                  f"{left:>8.3f}{right:>8.3f}{gap:>8.3f}{drift:>8.4f}")
    print()
    print(f"{checked} phases measured against the archive, {skipped} not in it. "
          f"{gripping} grip with both hands.")
    print(f"worst fan gap, SYMMETRIC holds only (within "
          f"{SYMMETRIC_DEGREES:.0f} degrees of a mirror):")
    print(f"  {worst_mirror:.4f} cm at {mirror_row}")
    print(f"worst fan drift, SAME population, when the ball moves "
          f"{GIRDLE_TRAVEL_M * 100:.2f} cm:")
    print(f"  {worst_drift:.4f} cm at {drift_row}, which is "
          f"{worst_drift / worst_mirror:.2f} times the gap")
    print()
    print("BOTH NUMBERS COME FROM THE SAME POPULATION. A drift taken over every")
    print("phase reaches 0.3757 cm at bounce_pass/release, which is a")
    print("NON-HOLDING frame whose fan no mirror claim covers, and dividing that")
    print("by a symmetric-hold gap crosses two populations.")


if __name__ == "__main__":
    main()
