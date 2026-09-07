"""Per-figure pass or fail for the ball's anchor, against the 1 cm rule.

`pose_phase` places the ball at `shoulders + fromShouldersInArms * arm`. Every
term on that line comes from the job except `shoulders`, which this rig
supplies itself. So the ball's error is the shoulder midpoint's error, one for
one, and nothing attenuates it.

DO NOT SUBTRACT THE TWO BODIES' COLUMNS. This rig's midpoint sits 6 to 14 cm
below the engine's, and almost all of that is body shape: the arms are 48.547
against 52.680, and this rig is not a uniform scale of that athlete. The error
is the ENGINE'S VARIATION from the phase this rig is calibrated to, because
this rig's own variation is zero.

THE FIRST VERSION OF THIS TABLE WAS VERTICAL ONLY AND UNDERSTATED THE ERROR.
The overhead pass's `lift` reads 7.41 cm vertically and 8.451 cm in three
axes, because the midpoint also travels 4.08 cm fore-and-aft. A whole
tolerance hid in an axis nobody had measured. `bounce_pass` is the sharper
case: it barely moves vertically at all, so a vertical-only column would have
called it the cleanest drill in the library.
"""

# Shoulder midpoint minus pelvis (`root`), cm, engine axes: across, up, ahead.
# These are the MOVEMENT LANE'S measured values, reported 2026-09-04, from the
# solved pose at frame round(atPhase * (frames - 1)). They are a snapshot of
# another lane's instrument, not a reading taken here.
ENGINE = {
    "bounce_pass": [
        ("ready", -0.007, 48.823, 2.463),
        ("pull_to_side", 0.009, 48.541, 1.231),
        ("drive", 0.014, 48.610, 0.952),
        ("release", 0.001, 48.675, 0.538),
        ("follow_through", 0.003, 48.609, 2.764)],
    "chest_pass": [
        ("ready", 0.002, 48.825, 2.462),
        ("step", 0.002, 48.836, 2.471),
        ("drive", -0.001, 50.270, 2.874),
        ("release", -0.001, 50.782, 2.867),
        ("follow_through", -0.003, 50.273, 3.121)],
    "deflect_high": [
        ("ready", -0.000, 56.284, -0.084),
        ("contact", -0.453, 54.519, 1.558),
        ("control", -0.027, 54.453, 1.927),
        ("send_on", 0.005, 52.479, 3.194)],
    "double_foot_landing": [
        ("approach", -0.000, 50.113, 2.727),
        ("flight", -0.001, 49.788, 2.664),
        ("land", 0.002, 50.505, 2.930),
        ("absorb", -0.002, 48.773, 2.426)],
    "hooks_jump_pull_in": [
        ("gather", -0.002, 50.275, 2.759),
        ("contact", -0.000, 54.130, 1.740),
        ("pull_in", -0.002, 49.915, 2.790),
        ("release", -0.001, 50.904, 3.199)],
    "hooks_outside_hand": [
        ("facing_away", 1.776, 48.883, 1.564),
        ("contact", 0.932, 50.215, 2.426),
        ("gather", 0.638, 50.810, 2.895),
        ("pull_in", 0.171, 48.764, 2.330)],
    "one_hand_snatch_to_other_hand": [
        ("ready", -0.061, 49.227, 2.489),
        ("reach", -0.058, 49.263, 2.483),
        ("contact", 0.006, 50.432, 2.645),
        ("join", 0.019, 50.911, 2.982),
        ("pull_in", 0.006, 48.762, 2.343)],
    "overhead_pass": [
        ("ready", -0.000, 48.826, 2.470),
        ("lift", -0.000, 56.231, -1.608),
        ("step", -0.000, 56.189, -1.436),
        ("release", -0.000, 55.391, 0.441),
        ("follow_through", -0.002, 52.206, 3.221)],
    "two_hand_catch_chest": [
        ("ready", -0.002, 49.729, 2.661),
        ("contact", 0.000, 51.454, 2.514),
        ("pull_in", -0.000, 48.922, 2.486),
        ("release", -0.002, 50.571, 3.164)],
    "two_hand_snatch_pull_in": [
        ("ready", 0.002, 49.766, 2.668),
        ("react", 0.001, 49.767, 2.668),
        ("contact", -0.001, 51.890, 2.696),
        ("pull_in", -0.001, 48.766, 2.344)],
    "two_hand_snatch_straight_back": [
        ("ready", 0.002, 49.766, 2.668),
        ("contact", 0.001, 51.758, 2.579),
        ("control", 0.002, 51.497, 3.015),
        ("return", 0.003, 50.575, 3.169)],
}

# Ball centre to head centre on THIS rig, cm, for all 43 phases of the 10
# drills the render library holds. `bounce_pass` is absent, and the report
# below says so rather than passing it silently.
BALL_TO_HEAD = {
    ("chest_pass", "ready"): 27.085,
    ("chest_pass", "step"): 27.432,
    ("chest_pass", "drive"): 34.392,
    ("chest_pass", "release"): 40.596,
    ("chest_pass", "follow_through"): 216.584,
    ("deflect_high", "ready"): 189.302,
    ("deflect_high", "contact"): 35.398,
    ("deflect_high", "control"): 29.209,
    ("deflect_high", "send_on"): 178.550,
    ("double_foot_landing", "approach"): 186.815,
    ("double_foot_landing", "flight"): 159.590,
    ("double_foot_landing", "land"): 30.196,
    ("double_foot_landing", "absorb"): 28.793,
    ("hooks_jump_pull_in", "gather"): 186.656,
    ("hooks_jump_pull_in", "contact"): 37.608,
    ("hooks_jump_pull_in", "pull_in"): 26.892,
    ("hooks_jump_pull_in", "release"): 83.842,
    ("hooks_outside_hand", "facing_away"): 173.791,
    ("hooks_outside_hand", "contact"): 47.395,
    ("hooks_outside_hand", "gather"): 28.665,
    ("hooks_outside_hand", "pull_in"): 27.801,
    ("one_hand_snatch_to_other_hand", "ready"): 187.551,
    ("one_hand_snatch_to_other_hand", "reach"): 164.902,
    ("one_hand_snatch_to_other_hand", "contact"): 45.844,
    ("one_hand_snatch_to_other_hand", "join"): 29.155,
    ("one_hand_snatch_to_other_hand", "pull_in"): 27.792,
    ("overhead_pass", "ready"): 27.090,
    ("overhead_pass", "lift"): 24.549,
    ("overhead_pass", "step"): 25.177,
    ("overhead_pass", "release"): 31.610,
    ("overhead_pass", "follow_through"): 202.001,
    ("two_hand_catch_chest", "ready"): 187.532,
    ("two_hand_catch_chest", "contact"): 48.330,
    ("two_hand_catch_chest", "pull_in"): 27.457,
    ("two_hand_catch_chest", "release"): 102.976,
    ("two_hand_snatch_pull_in", "ready"): 187.440,
    ("two_hand_snatch_pull_in", "react"): 187.441,
    ("two_hand_snatch_pull_in", "contact"): 44.200,
    ("two_hand_snatch_pull_in", "pull_in"): 27.794,
    ("two_hand_snatch_straight_back", "ready"): 187.441,
    ("two_hand_snatch_straight_back", "contact"): 46.602,
    ("two_hand_snatch_straight_back", "control"): 30.123,
    ("two_hand_snatch_straight_back", "return"): 124.764,
}

RADIUS = 11.00
ARM_HERE, ARM_ENGINE = 48.547, 52.680
SCALE = ARM_HERE / ARM_ENGINE
THRESHOLD = 1.0
# Past this the ball has left her hands. The anchor error is then a fraction of
# a flight distance, and no coach reads a cue from it.
IN_FLIGHT_CM = 100.0
NEUTRAL = ("chest_pass", "ready")


def offset_from(neutral, row) -> float:
    """Distance in three axes, cm."""
    return sum((a - b) ** 2 for a, b in zip(row, neutral)) ** 0.5


def main() -> None:
    neutral = next(row[1:] for row in ENGINE[NEUTRAL[0]] if row[0] == NEUTRAL[1])
    check = next(row[1:] for row in ENGINE["overhead_pass"] if row[0] == "ready")
    print("THE CALIBRATION POINT IS EVIDENCED, NOT ASSUMED.")
    print("  chest_pass/ready and overhead_pass/ready are two independent "
          "drills' neutral")
    print(f"  girdles, and they agree to {offset_from(neutral, check):.4f} cm "
          f"in three axes.")
    print("  deflect_high/ready and hooks_jump/gather are also frame-0 and do "
          "NOT agree with")
    print("  them, because those drills open with the arms already up. That is "
          "what makes")
    print("  the agreement of the other two a signal rather than a "
          "coincidence.")
    print()
    print(f"{'drill / phase':<40}{'across':>8}{'up':>8}{'ahead':>8}{'3D':>8}"
          f"{'scaled':>8}{'radius':>8}{'ball-head':>11}  verdict")
    fails = held = missing = total = 0
    for drill, rows in ENGINE.items():
        for name, across, up, ahead in rows:
            error = offset_from(neutral, (across, up, ahead))
            columns = (f"{drill + '/' + name:<40}{across:>8.3f}{up:>8.3f}"
                       f"{ahead:>8.3f}{error:>8.3f}{error * SCALE:>8.3f}"
                       f"{error / RADIUS * 100:>7.1f}%")
            reach = BALL_TO_HEAD.get((drill, name))
            if reach is None:
                missing += 1
                print(f"{columns}{'no job':>11}  NOT IN THE RENDER LIBRARY")
                continue
            total += 1
            flight = reach > IN_FLIGHT_CM
            if error > THRESHOLD:
                fails += 1
                held += 0 if flight else 1
                verdict = "fail (ball in flight)" if flight else "FAIL"
            else:
                verdict = "PASS"
            print(f"{columns}{reach:>11.2f}  {verdict}")
    print()
    print(f"{total - fails} of {total} rendered phases pass the "
          f"{THRESHOLD:.0f} cm rule. {fails} fail, and {held} of those")
    print("are HELD phases, where the ball is in her hands and a coach reads a "
          "cue from it.")
    drills = sum(1 for drill in ENGINE if any(
        (drill, row[0]) in BALL_TO_HEAD for row in ENGINE[drill]))
    print(f"Every one of the {drills} drills in the library has at least one "
          f"failing phase.")
    if missing:
        print()
        print(f"{missing} phases have NO JOB FILE in `spikes/poc-output`, so "
              f"this lane cannot render them.")
        print("They are counted nowhere above. A drill the renderer never sees "
              "is not a passing drill.")


if __name__ == "__main__":
    main()
