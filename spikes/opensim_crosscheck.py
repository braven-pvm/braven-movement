"""Cross-check the ISB measurement layer against OpenSim, then measure noise.

This spike answers two questions that decide the product claim.

1. Does our angle maths agree with the accepted biomechanics engine? OpenSim
   builds an arm whose elbow angle is known exactly. We read only the landmark
   positions, rebuild the segment frames, and compare our angle against the
   OpenSim coordinate.
2. How accurate must the landmarks be? A pose estimator does not give exact
   landmarks. We add noise of a known size and measure the angle error that
   results. The clinical threshold is 5 degrees, so this tells us the landmark
   budget.

Run it with the virtual environment interpreter, because it needs OpenSim.
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import opensim  # noqa: E402

from isb_angles import build_segment_frame, elbow_angles  # noqa: E402


HUMERUS_LENGTH_M = 0.32
FOREARM_LENGTH_M = 0.27
EPICONDYLE_OFFSET_M = 0.04
STYLOID_OFFSET_M = 0.03
DEGREES_PER_RADIAN = 180.0 / math.pi


def build_arm() -> tuple[opensim.Model, opensim.Coordinate]:
    """Build a two-segment arm with a pin elbow and anatomical markers."""
    model = opensim.Model()
    model.setName("braven_crosscheck_arm")

    inertia = opensim.Inertia(0.01, 0.01, 0.01)
    humerus = opensim.Body("humerus", 2.0, opensim.Vec3(0.0), inertia)
    forearm = opensim.Body("forearm", 1.5, opensim.Vec3(0.0), inertia)
    model.addBody(humerus)
    model.addBody(forearm)

    # The humerus is welded to ground so that only the elbow moves. The elbow is
    # a pin joint, so its coordinate is exactly the flexion angle.
    shoulder = opensim.WeldJoint(
        "shoulder",
        model.getGround(),
        opensim.Vec3(0.0),
        opensim.Vec3(0.0),
        humerus,
        opensim.Vec3(0.0),
        opensim.Vec3(0.0),
    )
    elbow = opensim.PinJoint(
        "elbow",
        humerus,
        opensim.Vec3(0.0, -HUMERUS_LENGTH_M, 0.0),
        opensim.Vec3(0.0),
        forearm,
        opensim.Vec3(0.0),
        opensim.Vec3(0.0),
    )
    model.addJoint(shoulder)
    model.addJoint(elbow)

    # Markers stand for the landmarks a pose estimator or a coach would supply.
    # The lateral points sit on the negative Z side so that a positive pin
    # rotation reads as positive flexion in the ISB frame.
    markers = {
        "shoulder_centre": (humerus, (0.0, 0.0, 0.0)),
        "elbow_centre": (humerus, (0.0, -HUMERUS_LENGTH_M, 0.0)),
        "lateral_epicondyle": (
            humerus,
            (0.0, -HUMERUS_LENGTH_M, -EPICONDYLE_OFFSET_M),
        ),
        "wrist_centre": (forearm, (0.0, -FOREARM_LENGTH_M, 0.0)),
        "radial_styloid": (forearm, (0.0, -FOREARM_LENGTH_M, -STYLOID_OFFSET_M)),
    }
    for name, (body, location) in markers.items():
        model.addMarker(opensim.Marker(name, body, opensim.Vec3(*location)))

    model.finalizeConnections()
    coordinate = model.getCoordinateSet().get(0)
    return model, coordinate


def landmark_positions(model: opensim.Model, state) -> dict[str, tuple[float, float, float]]:
    positions: dict[str, tuple[float, float, float]] = {}
    marker_set = model.getMarkerSet()
    for index in range(marker_set.getSize()):
        marker = marker_set.get(index)
        point = marker.getLocationInGround(state)
        positions[marker.getName()] = (point.get(0), point.get(1), point.get(2))
    return positions


def measured_flexion(points: dict[str, tuple[float, float, float]]) -> float:
    humerus = build_segment_frame(
        distal_point=points["elbow_centre"],
        proximal_point=points["shoulder_centre"],
        lateral_point=points["lateral_epicondyle"],
        name="humerus",
    )
    forearm = build_segment_frame(
        distal_point=points["wrist_centre"],
        proximal_point=points["elbow_centre"],
        lateral_point=points["radial_styloid"],
        name="forearm",
    )
    return elbow_angles(humerus=humerus, forearm=forearm).degrees[0]


def perturb(
    points: dict[str, tuple[float, float, float]],
    sigma_m: float,
    generator: random.Random,
) -> dict[str, tuple[float, float, float]]:
    return {
        name: tuple(value + generator.gauss(0.0, sigma_m) for value in point)  # type: ignore[misc]
        for name, point in points.items()
    }


def run_exactness_sweep(model: opensim.Model, coordinate, state) -> float:
    print("Exactness against OpenSim")
    print(f"{'OpenSim degrees':>16} {'ISB layer degrees':>19} {'difference':>12}")
    worst = 0.0
    for target in (0.0, 15.0, 30.0, 45.0, 60.0, 90.0, 120.0, 145.0):
        coordinate.setValue(state, target / DEGREES_PER_RADIAN)
        model.realizePosition(state)
        measured = measured_flexion(landmark_positions(model, state))
        difference = abs(measured - target)
        worst = max(worst, difference)
        print(f"{target:16.2f} {measured:19.4f} {difference:12.6f}")
    print(f"worst difference: {worst:.6f} degrees\n")
    return worst


def run_noise_study(model: opensim.Model, coordinate, state) -> None:
    print("Landmark noise against angle error")
    print("Each row perturbs every landmark with Gaussian noise, 400 samples.")
    print(
        f"{'landmark noise':>15} {'mean error':>12} {'95th percentile':>17} "
        f"{'over 5 deg':>11}"
    )
    coordinate.setValue(state, 110.0 / DEGREES_PER_RADIAN)
    model.realizePosition(state)
    truth = landmark_positions(model, state)
    exact = measured_flexion(truth)
    for sigma_mm in (2.0, 5.0, 10.0, 20.0, 40.0):
        generator = random.Random(20260817)
        errors = []
        for _ in range(400):
            noisy = perturb(truth, sigma_mm / 1000.0, generator)
            errors.append(abs(measured_flexion(noisy) - exact))
        errors.sort()
        mean = sum(errors) / len(errors)
        percentile = errors[int(0.95 * len(errors))]
        over = sum(1 for value in errors if value > 5.0) / len(errors)
        print(
            f"{sigma_mm:12.0f} mm {mean:9.2f} deg {percentile:14.2f} deg "
            f"{over * 100:9.1f} %"
        )
    print()


def main() -> int:
    model, coordinate = build_arm()
    state = model.initSystem()

    worst = run_exactness_sweep(model, coordinate, state)
    run_noise_study(model, coordinate, state)

    if worst > 0.001:
        print(f"FAIL the ISB layer disagrees with OpenSim by {worst:.4f} degrees")
        return 1
    print("PASS the ISB layer reproduces the OpenSim elbow angle exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
