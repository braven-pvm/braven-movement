"""Where the ball sits relative to the hand, on the refused pose and the rest.

The flexion is applied in the plane that turns the finger toward the BALL, not
about the bone's own x. So the axis that carries the flexion is decided by where
the ball is RELATIVE TO THE HAND. This measures that, so the paper can say why
one pose of twelve turns about z.

NEUTRALISES `axis_complaint` FOR THIS PROCESS ONLY, so the refused pose can be
measured at all. Nothing on disk changes and the renderer is untouched: the
substitution lives in this process's own module objects and dies with it. It is
here because a frame the guard refuses cannot otherwise be measured, and
"could not measure it" is not a finding.

    blender -b --python-exit-code 9 -P scripts/ball_off_finger_line.py --
"""

import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for extra in (REPO, REPO / "spikes"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import finger_curl  # noqa: E402

finger_curl.axis_complaint = lambda *a, **k: None
import blender_mpfb_reference_catch as reference  # noqa: E402

reference.axis_complaint = lambda *a, **k: None

import blender_movement_render as R  # noqa: E402
from blender_mpfb_reference_catch import world_head, world_tail  # noqa: E402
from reference_pose_config import load_reference_catch_config  # noqa: E402

JOBS = sorted((REPO / "spikes" / "poc-output").glob("*.job.json"))


def main() -> None:
    studio = R.Studio(load_reference_catch_config())
    print(f"{'drill / phase':<40}{'side':>5}{'ball off the':>14}"
          f"{'ball off the':>14}")
    print(f"{'':<40}{'':>5}{'finger line':>14}{'palm plane':>14}")
    rows = []
    for path in JOBS:
        job = json.loads(path.read_text(encoding="utf-8"))
        drill = job["movementId"].replace("netball_", "")
        for phase in job["phases"]:
            grip = phase.get("grip") or {}
            if not grip:
                continue
            try:
                centre, _ = R.pose_phase(
                    studio.rig, phase, job["anatomyLimitsDegrees"],
                    studio.basis, studio.foot_baseline,
                    studio.config.finger_curl_degrees,
                    job.get("knuckleLimitsDegrees"), studio.human)
            except Exception:
                continue
            for side in grip:
                knuckle = world_head(studio.rig, f"index_01_{side}")
                tip = world_tail(studio.rig, f"index_03_{side}")
                along = (tip - knuckle).normalized()
                toward = (centre - knuckle).normalized()
                # How far the ball sits off the line the finger points along.
                off_finger = math.degrees(math.acos(
                    max(-1.0, min(1.0, along.dot(toward)))))
                # And how far it sits out of the plane the finger swings in,
                # which is the plane containing the finger and the hand's own
                # across axis. Out of that plane, the flexion has to turn about
                # something else.
                across = (world_head(studio.rig, f"index_01_{side}")
                          - world_head(studio.rig, f"pinky_01_{side}"))
                if across.length < 1e-9:
                    continue
                normal = along.cross(across.normalized())
                if normal.length < 1e-9:
                    continue
                out_of_plane = 90.0 - math.degrees(math.acos(
                    max(-1.0, min(1.0, abs(normal.normalized().dot(toward))))))
                rows.append((f"{drill}/{phase['name']}", side, off_finger,
                             abs(out_of_plane)))
    rows.sort(key=lambda r: r[3])
    for row in rows[:5]:
        print(f"{row[0]:<40}{row[1]:>5}{row[2]:>14.1f}{row[3]:>14.1f}")
    print("   ...")
    for row in rows[-6:]:
        print(f"{row[0]:<40}{row[1]:>5}{row[2]:>14.1f}{row[3]:>14.1f}")
    print()
    high = [r for r in rows if "one_hand_high" in r[0]]
    print("the twelfth drill:")
    for row in high:
        print(f"  {row[0]:<38}{row[1]:>5}{row[2]:>14.1f}{row[3]:>14.1f}")
    print()
    print("`ball off the palm plane` is how far out of the finger's own swing")
    print("plane the ball sits. The flexion turns the finger TOWARD the ball,")
    print("so the further out of that plane the ball is, the less of the turn")
    print("the bone's own flexion axis can carry.")


if __name__ == "__main__":
    main()
