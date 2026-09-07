"""What a coach would see under each option for the wrist at the release frame.

THIS CHOOSES NOTHING. The wrist encoding is a contract question and it is put
to Marius with numbers beside each option, not settled here.

THE SITUATION. The renderer places a wrist by one of two formulae and picks
between them on `ball.holding`:

    not holding   shoulder + direction * (reachFraction * reach)
    holding       ballCentre + outward * (radius + wristFromSurfaceInArms * reach)

`holding` goes False AT the release frame, so the formula changes in a single
frame. The two agree to 0.000 mm on the body the engine solves, because that is
where they were authored. They do not agree on this one, because the ball's
radius is one absolute size and does not scale with the athlete.

On the shipped library the release frames are the only deep intersections in
the whole set: 9.55 to 20.27 mm of ball inside the mesh, against 0.05 to 1.65 mm
on every holding phase, where the fingers are pressing on the surface and are
meant to be.

    blender -b --python-exit-code 9 -P scripts/wrist_release_options.py --
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for extra in (REPO, REPO / "spikes"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import blender_movement_render as R  # noqa: E402
from blender_mpfb_reference_catch import world_head  # noqa: E402
from reference_pose_config import load_reference_catch_config  # noqa: E402

JOBS = sorted((REPO / "spikes" / "poc-output").glob("*.job.json"))


def pose(studio, job, phase):
    """EXACTLY as `render_job` calls it: the JOB's limits, both of them."""
    return R.pose_phase(
        studio.rig, phase, job["anatomyLimitsDegrees"], studio.basis,
        studio.foot_baseline, studio.config.finger_curl_degrees,
        job.get("knuckleLimitsDegrees"), studio.human,
    )


def carried(phase: dict, previous: dict) -> dict:
    """The release phase, holding the grip the previous phase used.

    This is OPTION B in the crudest form: the ball keeps deciding where the
    hands go for one more frame. It is not a proposal for how a blend would be
    written; it is what the ball-relative formula puts on the page.
    """
    changed = json.loads(json.dumps(phase))
    changed["grip"] = json.loads(json.dumps(previous["grip"]))
    changed["ball"] = json.loads(json.dumps(phase["ball"]))
    changed["ball"]["holding"] = True
    return changed


def report(studio, receipt) -> tuple:
    body = receipt.get("bodyClearanceMm") or {}
    wrists = {
        side: tuple(world_head(studio.rig, f"hand_{side}")) for side in ("l", "r")
    }
    return body.get("verticesInside", 0), body.get("deepestMm", 0.0), wrists


def main() -> None:
    studio = R.Studio(load_reference_catch_config())
    print(f"{'drill / phase':<34}{'option':<10}{'inside':>8}{'deepest':>10}"
          f"{'wrist moves':>13}")
    for path in JOBS:
        job = json.loads(path.read_text(encoding="utf-8"))
        drill = job["movementId"].replace("netball_", "")
        phases = job["phases"]
        for index, phase in enumerate(phases):
            if phase["ball"].get("holding") or index == 0:
                continue
            previous = phases[index - 1]
            if not previous.get("grip"):
                continue
            _, shipped = pose(studio, job, phase)
            pick_inside, pick_deep, pick_wrists = report(studio, shipped)
            if pick_inside == 0 and pick_deep == 0.0:
                continue

            _, held = pose(studio, job, carried(phase, previous))
            hold_inside, hold_deep, hold_wrists = report(studio, held)
            moved = max(
                (R.Vector(pick_wrists[side]) - R.Vector(hold_wrists[side])).length
                for side in ("l", "r")
            ) * 1000.0

            label = f"{drill}/{phase['name']}"
            print(f"{label:<34}{'A pick':<10}{pick_inside:>8}"
                  f"{pick_deep:>10.2f}{'':>13}")
            print(f"{'':<34}{'B ball':<10}{hold_inside:>8}"
                  f"{hold_deep:>10.2f}{moved:>12.1f}mm")
    print()
    print("OPTION A, PICK, is what ships today. The wrist leaves the ball in one")
    print("frame and the ball passes through the hand on the way out.")
    print("OPTION B, BALL, keeps the ball deciding for that frame. The hand stays")
    print("on the ball, and the arm no longer matches what `arms` asked for.")
    print()
    print("A coach reads the release for whether the hands leave the ball")
    print("together and where they point. Neither option is free, and this lane")
    print("does not choose between them.")


if __name__ == "__main__":
    main()
