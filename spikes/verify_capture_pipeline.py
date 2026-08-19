"""Prove the capture path works before the footage arrives.

The field capture cannot be tested with real footage yet, so this stands in for
it. A known pose is projected into cameras placed where the capture card says to
put them. Those projections are fed to the same fitter that will receive the real
detections, and the recovered angles are compared against the truth.

The check is not whether the fit is good. It is whether the engine is honest: no
angle it shows a coach may be wrong by more than the clinical threshold. An angle
it cannot determine must be withheld, and the engine has to work that out without
seeing the truth.

    pixi run python verify_capture_pipeline.py
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np

SPIKE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SPIKE_DIR))

from motion_track import load_motion  # noqa: E402
from movement_engine import load_character, motion_path, solve  # noqa: E402
from multi_camera_fit import (  # noqa: E402
    MEANINGFUL_DEGREES,
    Camera,
    View,
    estimate_uncertainty,
    fit,
    judge,
    measure,
    report,
)

MOVEMENT = "netball_two_hand_snatch_pull_in"
# The landmarks a detector reports. No fingertips.
OBSERVED = (
    "c_head", "c_neck", "root",
    "l_uparm", "l_lowarm", "l_wrist",
    "r_uparm", "r_lowarm", "r_wrist",
    "l_upleg", "l_lowleg", "l_foot",
    "r_upleg", "r_lowleg", "r_foot",
)
FRAME = (1080, 1920)
DETECTOR_NOISE_PX = 2.0
SEED = 20260818


def build_view(
    name: str,
    azimuth: float,
    centre: np.ndarray,
    points: np.ndarray,
    index: dict[str, int],
    noise_px: float,
    generator: random.Random,
) -> View:
    """Project the truth pose into this camera, as a detector would see it."""
    camera = Camera(
        name=name,
        azimuth_degrees=azimuth,
        height_cm=0.0,
        distance_cm=320.0,
        width_px=FRAME[0],
        height_px=FRAME[1],
    )
    projection = camera.projection(centre).astype(np.float64)
    landmarks: dict[str, tuple[float, float]] = {}
    for joint in OBSERVED:
        homogeneous = projection @ np.array([*points[index[joint]], 1.0])
        pixel = homogeneous[:2] / homogeneous[2]
        if noise_px > 0.0:
            pixel = pixel + np.array(
                [generator.gauss(0.0, noise_px), generator.gauss(0.0, noise_px)]
            )
        landmarks[joint] = (float(pixel[0]), float(pixel[1]))
    return View(camera=camera, landmarks=landmarks)


def main() -> int:
    character = load_character()
    track = load_motion(motion_path(MOVEMENT))
    result = solve(character, track)
    index = result["index"]

    contact = round(track.contact_phase() * (len(result["points"]) - 1))
    truth_points = result["points"][contact]
    truth = measure(truth_points, index)
    centre = truth_points[index["c_neck"]]

    print(f"truth pose: {MOVEMENT}, contact frame {contact}")
    for name, value in truth.items():
        print(f"  {name:<34} {value:7.2f} deg")

    setups = {
        "one camera": [0.0],
        "two, 20 degrees apart": [-10.0, 10.0],
        "two, 60 degrees apart": [-30.0, 30.0],
        "two, 90 degrees apart": [-45.0, 45.0],
    }

    print(f"\nrecovery with {DETECTOR_NOISE_PX:.0f} px of detector noise")
    header = f"{'setup':<24} {'shown':>6} {'hidden':>7} {'worst shown':>13}"
    print(header)

    rows = []
    for label, azimuths in setups.items():
        generator = random.Random(SEED)
        views = [
            build_view(
                f"cam{number}",
                azimuth,
                centre,
                truth_points,
                index,
                DETECTOR_NOISE_PX,
                generator,
            )
            for number, azimuth in enumerate(azimuths)
        ]
        verdict = judge(views)
        fitted = fit(character, views, centre)
        recovered = measure(fitted["points"], fitted["index"])
        # The engine estimates its own uncertainty, with no access to the truth.
        spread = estimate_uncertainty(
            character, views, centre, detector_noise_px=DETECTOR_NOISE_PX
        )
        decided = report(recovered, spread, verdict)

        shown = [name for name, row in decided.items() if row["shown"]]
        hidden = [name for name, row in decided.items() if not row["shown"]]
        worst_shown = max(
            (abs(recovered[name] - truth[name]) for name in shown), default=0.0
        )
        print(
            f"{label:<24} {len(shown):>6} {len(hidden):>7} {worst_shown:12.2f} deg"
        )
        rows.append(
            {
                "setup": label,
                "cameras": len(views),
                "separationDegrees": verdict.separation_degrees,
                "measurementValid": verdict.measurement_valid,
                "shown": shown,
                "hidden": hidden,
                "worstShownErrorDegrees": round(worst_shown, 2),
                "angles": {
                    name: {
                        "shown": row["shown"],
                        "uncertaintyDegrees": row["uncertaintyDegrees"],
                        "actualErrorDegrees": round(
                            abs(recovered[name] - truth[name]), 2
                        ),
                    }
                    for name, row in decided.items()
                },
            }
        )

    output = SPIKE_DIR / "poc-output" / "capture_pipeline.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"movement": MOVEMENT, "truth": truth, "recovery": rows}, indent=2)
        + "\n",
        encoding="utf-8",
    )

    print("\nwhat the engine chose to hide, and whether it was right to")
    for row in rows:
        if not row["hidden"]:
            continue
        worst_hidden = max(
            row["angles"][name]["actualErrorDegrees"] for name in row["hidden"]
        )
        print(
            f"  {row['setup']:<24} hid {len(row['hidden'])}, "
            f"worst hidden error {worst_hidden:.2f} deg"
        )

    print(f"\nreceipt: {output}")

    failures = [
        row for row in rows if row["worstShownErrorDegrees"] > MEANINGFUL_DEGREES
    ]
    if failures:
        for row in failures:
            print(
                f"FAIL {row['setup']} showed an angle wrong by "
                f"{row['worstShownErrorDegrees']:.2f} degrees"
            )
        return 1
    print("PASS every angle the engine showed is inside the clinical threshold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
