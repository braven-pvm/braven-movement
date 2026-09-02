"""A waiting hand must be able to reach where it is asked to wait.

`toward` places the waiting point at a fixed distance from the MIDPOINT of the
shoulders, and its docstring says "no further out than she reaches". For a
square athlete that is true, because both shoulders are the same distance from
the middle. For a TURNED athlete it is false: on `netball_hooks_outside_hand`,
which starts facing away at -44 degrees, a point 50.8 cm from the midpoint sat
66.4 cm from her left shoulder and 39.1 cm from her right.

She waited with that arm locked out at 0.93 to 0.999 of full extension, where
every other arm in the library waits between 0.33 and 0.89. Worse, a hand
target past full reach has no elbow triangle, so `elbow_poles` skipped that arm
entirely: the elbow was unconstrained for 41 frames, drifted 46 degrees from
where the pole wanted it, and was corrected all at once when the target came
inside her reach. That single frame was the largest step in the library.

The check invents no number. It measures what the library's own arms do while
they wait and requires every arm to stay inside that. A drill that locks an
elbow out fails against its own neighbours rather than against a threshold
somebody chose.

These run only where the solver is installed, which is the pixi environment.
A green system-python run says nothing about them.
"""

from __future__ import annotations

import unittest

import numpy as np

# Only a genuinely absent solver may skip. Catching every exception here would
# swallow a break in the code under test and skip the guard in silence.
try:
    import pymomentum.geometry  # noqa: F401

    SOLVER = True
except ImportError:  # pragma: no cover - exercised only without the solver
    SOLVER = False

# THE READY STANCE OF EVERY DRILL, in degrees of shoulder-line turn at frame 0,
# measured on c4a7a37. These are RECORDED FACTS and not targets: nothing was
# tuned to reach them and no threshold was chosen to make them pass.
#
# The build matters and an earlier draft named the wrong one. It said fc29bb2,
# where `netball_chest_pass` DID NOT EXIST — the drill arrived two merges
# later. A figure whose named build could not have produced it is not sourced.
#
# `netball_bounce_pass` was measured on 32663a9 plus its own pack, by its author,
# with the same `ground_angle("l_uparm", "r_uparm")` expression this file uses on
# frame 0. THE AUTHOR OF A DRILL ADDS ITS PIN, ruled 2026-09-02 after a merge race
# left `netball_overhead_pass` unpinned: #61 added this guard and #60 added that
# drill, each green alone and red together, and no hosted run could see it because
# the runner has no solver. On the same run the overhead pass read -0.0110 against
# the -0.011 the movement lane measured independently, so the two instruments agree.
STANCE_DEGREES = {
    "netball_bounce_pass": 0.035,
    "netball_chest_pass": -0.004,
    "netball_deflect_high": -0.000,
    "netball_double_foot_landing": 0.034,
    "netball_hooks_jump_pull_in": -0.020,
    "netball_hooks_outside_hand": -48.217,
    "netball_one_hand_snatch_to_other_hand": -0.496,
    # ADDED AS A HOTFIX in PR #64. This drill arrived in PR #60 while the guard
    # above arrived in PR #57. Each tip was green on its own and the merged
    # tree was red, because the guard sweeps the library rather than checking a
    # fixed list. Hosted CI cannot catch that: the runner has no assets, so it
    # never solves and the guard never runs there. The local suite on the
    # merged tree is the only instrument for this.
    "netball_overhead_pass": -0.011,
    "netball_two_hand_catch_chest": -0.018,
    "netball_two_hand_snatch_pull_in": 0.019,
    "netball_two_hand_snatch_straight_back": 0.020,
}
# THE PELVIS LINE IS DELIBERATELY NOT PINNED, and that is a finding rather than
# an omission. It was built as a pin and the pin was withdrawn before it shipped.
#
# The lower body MIRRORS under ordinary code changes, not only under changes to
# the enabled parameter set. Between the two configurations that shipped as
# 716b3eb and ac240b2, whose difference is the sign on one hand's finger spread,
# SIX of the nine drills flipped their pelvis line, worst move 61.45 degrees.
# Both states are RECONSTRUCTED on one engine rather than checked out:
#
#   double_foot_landing           -15.65 ->  15.69
#   hooks_jump_pull_in            -15.70 ->  15.65
#   hooks_outside_hand              6.05 -> -55.40
#   two_hand_catch_chest           15.66 -> -15.66
#   two_hand_snatch_pull_in        15.67 -> -15.66
#   two_hand_snatch_straight_back  15.67 -> -15.67
#
# A pin on that value would have gone RED on six drills for a correct, ruled,
# shipped change. That is the failure this file already rejects by name for the
# stance pin: a guard that fires on every legitimate change is noise within a
# week and deleted within two.
#
# Nor is the magnitude pinnable: |pelvis| is stable on eight drills across that
# transition and moves 6.05 to 55.40 on the ninth.
#
# THE SHOULDER LINE IS STABLE ACROSS THE SAME TRANSITION ON THE EIGHT SQUARE
# DRILLS — worst move 0.056 degrees — which is why it can be pinned there and
# the pelvis cannot.
#
# IT IS NOT STABLE ON THE NINTH. `hooks_outside_hand`'s shoulder line moves
# -48.234 to -15.442 across the same transition, 32.79 degrees, and an earlier
# draft of this comment said the upper body was unaffected at 0.041. That was
# read from the square drills alone and stated of all nine.
#
# So the same code change flipped ONE drill above the hips and SIX below it.
# The one above was ruled on and REVERSED by PR #53, which is what
# docs/CLAVICLE_ARTEFACT.md records. The six below were never ruled on at all,
# and that is what withdraws the pin: a pelvis pin would go red on six drills
# nobody has decided anything about. The square drills carry that argument by
# themselves and do not need the ninth.
#
# Refer to "The lower body has no stable solution" in docs/KNOWN_ISSUES.md.
# Wide enough to ignore ordinary drift, narrow enough to catch a basin flip.
#
# Ordinary drift on these is hundredths of a degree: across the hand-mirror fix
# and the locked-parameter fix, every square drill moved by 0.056 or less. The
# flip this exists for is 33 degrees. Two is far above the one and far below the
# other, and there is a great deal of room in between, so THE NUMBER IS NOT
# DELICATE — which is the property being aimed for. A guard whose threshold has
# to be right is a guard somebody will retune.
STANCE_TOLERANCE_DEGREES = 2.0

# THE LEFT-RIGHT KNEE GAP, in degrees, on every drill whose authoring is even.
#
# `technique.movement_carries_no_side()` names that population, and it reads
# ALL THREE of a movement's files because the solve reads all three. A mirrored
# athlete is what they ask for, so the gap between her knees should be zero. IT
# IS NOT. It is 3.93 to 6.48 degrees across the three configurations below, and
# 4.02 to 6.48 on the shipped build, on every drill in every solution measured.
#
# AN EARLIER VERSION READ THE MOTION FILE ALONE, WHICH IS THE WRONG FILE.
# A possession solve reads NO HAND KEYS — `solve_movement` says so in its own
# docstring — so the hands chase the BALL and the TECHNIQUE. Reading the motion
# file admitted `netball_deflect_high`, whose keys are perfectly even and whose
# ball ARRIVES 0.28 arm lengths to her left while its technique carries the
# ball from +0.224 to -0.203, straight across her body. It is now excluded by
# its ball and by its technique independently, and the rendering handoff
# already called that contact asymmetric by design.
#
# It was also the loudest member. Its configuration spread was 2.04 degrees
# against 0.70 or less for every drill that is genuinely even, which was
# visible in the table before the cause was, and it was read as a wide drill
# rather than as the wrong drill.
#
# WHERE THE SIGN COULD NOT BE PINNED, THE MAGNITUDE CAN. The pelvis line above
# flips between solutions, which is why no pin was possible on it. Two mirrored
# solutions read the SAME |left - right|, so this quantity survives exactly the
# change that defeated the other. Measured across three states — the finger
# negation, the shipped mirror, and the mirror with the locked parameters
# pinned — each drill moves by:
#
#   overhead_pass                  0.02      two_hand_snatch_pull_in  0.11
#   chest_pass                     0.25      two_hand_catch_chest     0.29
#   straight_back                  0.31      hooks_jump_pull_in       0.70
#
# The ceilings below are the WORST of those three states plus one degree. The
# margin is calibrated, not chosen: it sits above every basin move measured,
# the largest of which is 0.70.
#
# THE CALIBRATION POPULATION IS THREE, AND THEY ARE NAMED: the finger negation
# with the locked parameters free, the shipped mirror with them free, and the
# mirror with them pinned. Three is a small population, and all three are
# ENGINE-side changes. An engine change alters the solver's freedom; a key
# change moves the target it chases. These are different acts on the solver, so
# steadiness under the first is EVIDENCE that the ceilings are not noise and is
# not PROOF that they hold under the second. The sweep below shows they do not.
#
# A DRILL THAT HAD NEVER BEEN MEASURED HERE LANDED ON THE SAME NUMBERS.
# `netball_overhead_pass` was authored by another lane and merged while this
# branch was open. Both coverage guards went red by name, which is what they
# are for. It reads 6.26, 6.25 and 6.27 across the three configurations — a
# spread of 0.02, the tightest here — with square shoulders at -0.011 and a
# pelvis line of 15.607, 15.583 and -15.634.
#
# IT IS BLIND TO THIS FINDING BUT NOT INDEPENDENT OF IT, and the difference
# matters. Its stance is `hipDropFraction` 0.1003 with no feet, no turn and no
# root travel, which its own note says is copied from the chest catch and the
# chest pass. So it shares its lower-body authoring with the drills already in
# the table. What it shows is that EVERY PLANTED DRILL LANDS THERE, not that an
# unrelated one does.
#
# THE LEGS DO NOT DECIDE IT ALONE. The overhead reads 6.27 where the chest pass
# reads 4.31 on identical lower-body inputs, so the upper body's demand
# modulates the gap. That is a lead on where the instability lives and it is
# not a conclusion.
#
# A FOURTH SOLUTION COULD BREACH THESE, and that is not a reason to raise them.
# If one does, the finding is that a new basin exists; read "The lower body has
# no stable solution" in docs/KNOWN_ISSUES.md before touching a number here.
#
# WHAT THESE CEILINGS DO NOT COVER: A CHANGE TO A DRILL'S OWN KEYS.
#
# They are calibrated across three ENGINE configurations, and every drill stays
# inside them in all three. They are not a claim about the authoring. A lateral
# hip step planted into two_hand_catch_chest in equal increments of 0.01 gives:
#
#   0.00  4.44      0.01  3.49      0.02  5.85
#   0.03  2.24      0.04  7.05      0.05  1.80
#
# THE MEASURE IS NOT A CONTINUOUS FUNCTION OF ITS INPUT. It does not rise with
# the planted asymmetry; it oscillates across the whole range, and each step
# moves some joint by 4.5 to 8.0 cm. The same sweep on hooks_jump_pull_in's
# right foot behaves the same way. Every step lands in a different solution.
#
# So a red result here after a key change means "the lower body moved", which
# is true and is the moment to look. It does not mean the change was wrong, and
# the number must not be re-fitted to whatever the new keys produce.
#
# THE SOLVE ITSELF IS EXACTLY REPRODUCIBLE. Three runs of one drill on an
# unchanged tree agree to 0.0000 cm at every joint and to four decimals in the
# gap, so nothing in this table is a sampled average.
KNEE_GAP_CEILING_DEGREES = {
    "netball_chest_pass": 5.56,
    "netball_hooks_jump_pull_in": 7.48,
    "netball_overhead_pass": 7.27,
    "netball_two_hand_catch_chest": 5.44,
    "netball_two_hand_snatch_pull_in": 5.20,
    "netball_two_hand_snatch_straight_back": 5.24,
}
# What a fixed solver would read. Every measured value is above 3.78, and no
# quantity here is noisy at the tenth of a degree, so one degree separates
# "solved evenly" from "not solved evenly" with room on both sides.
KNEE_GAP_SOLVED_DEGREES = 1.0

if SOLVER:
    # Deliberately unguarded: a failure here is a real break and must be loud.
    from ball_track import has_ball
    from ball_track import ball_path, load_ball
    from motion_track import load_motion
    from movement_engine import library, load_character, motion_path
    from possession_solve import solve_movement
    from technique import movement_carries_no_side
    from technique import has_technique, load_technique, technique_path


@unittest.skipUnless(SOLVER, "needs pymomentum, which lives in the pixi environment")
class NoHandWaitsPastFullStretch(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        character = load_character()
        index = {
            name: number
            for number, name in enumerate(character.skeleton.joint_names)
        }
        cls.reaching: dict[tuple[str, str], float] = {}
        cls.waiting: dict[tuple[str, str], float] = {}
        cls.turned: dict[str, float] = {}
        cls.stance: dict[str, float] = {}
        cls.pelvis: dict[str, float] = {}
        cls.knee_gap: dict[str, float] = {}
        cls.even: dict[str, bool] = {}
        for movement_id in library():
            if not (has_ball(movement_id) and has_technique(movement_id)):
                continue
            method = load_technique(technique_path(movement_id))
            if not method.possession_ready:
                continue
            result = solve_movement(character, movement_id)
            points = result["points"]
            contact = result["possession"].contact_frame
            arm = float(result["armLengthCm"])

            # THE BASIN LINES ARE RECORDED BEFORE THE CONTACT CHECK BELOW.
            #
            # That check skips a drill whose contact frame is 0, which is every
            # drill that STARTS with the ball — the chest pass today. Recording
            # the stance after it meant the basin pin could not see the one
            # drill whose pelvis flip is easiest to demonstrate. Frame zero
            # exists whatever the contact frame is.
            first = points[0]

            def ground_angle(left: str, right: str) -> float:
                line = first[index[left]] - first[index[right]]
                line = line / np.linalg.norm(line)
                return float(np.degrees(np.arctan2(line[2], line[0])))

            # SIGNED. The sign IS the basin: a mirrored pose reads the same
            # magnitude and the opposite sign, so abs() would pass it.
            cls.stance[movement_id] = ground_angle("l_uparm", "r_uparm")
            cls.pelvis[movement_id] = ground_angle("l_upleg", "r_upleg")

            # The WORST gap over the whole drill, not the gap at one landmark.
            # An asymmetry that appears only under load would hide in a
            # frame-zero reading, and load is when a knee matters.
            cls.knee_gap[movement_id] = max(
                abs(
                    frame["leftKneeFlexionDegrees"]
                    - frame["rightKneeFlexionDegrees"]
                )
                for frame in result["measurements"]
            )
            cls.even[movement_id] = movement_carries_no_side(
                load_motion(motion_path(movement_id)),
                load_ball(ball_path(movement_id)) if has_ball(movement_id) else None,
                method,
            )

            if contact is None or contact < 1:
                continue
            cls.turned[movement_id] = abs(cls.stance[movement_id])
            for side in ("l", "r"):
                shoulder, wrist = index[f"{side}_uparm"], index[f"{side}_wrist"]
                worst = max(
                    float(np.linalg.norm(frame[wrist] - frame[shoulder])) / arm
                    for frame in points[:contact]
                )
                where = cls.reaching if side in method.sides else cls.waiting
                where[(movement_id, side)] = worst

    def test_the_library_has_a_hand_of_each_kind(self) -> None:
        """Guards the guard. The comparison below is empty without both."""
        self.assertTrue(self.reaching, "no drill reaches for the ball")
        self.assertTrue(self.waiting, "no drill has a hand that waits")

    def test_each_drill_still_stands_the_way_it_stood(self) -> None:
        """THE BASIN PIN. Each drill's ready stance, recorded per drill.

        `netball_hooks_outside_hand` has TWO solved poses about 33 degrees apart
        in ready-stance turn, and which one the solver reaches depends on the
        COMPOSITION of the enabled parameter set rather than on any parameter in
        it. Excluding an unrelated axis with a real range moves it, and so does
        excluding either foot. Refer to docs/CLAVICLE_ARTEFACT.md.

        Nothing reported that flip for a day. It moved no verdict, it moved no
        aggregate — the two-handed contact mean read 36.40 to 36.43 through all
        of it — and four published findings were written from the wrong pose
        before two other guards caught it by accident.

        WHY A PIN AND NOT A FINGERPRINT. A pose fingerprint would go red on
        every legitimate change: the hand fix moved 46 graded values and the
        locked-parameter fix moved 42. A guard that fires on all of those is
        noise within a week and deleted within two. What discriminates is the
        GAP: ordinary drift here is hundredths of a degree and a basin flip is
        33, so a tolerance anywhere between them catches one and ignores the
        other.

        ITS BLIND SPOT IS MEASURED, NOT SUSPECTED, and it is worse than the
        first version of this docstring guessed. That version said the square
        drills "would read near zero in either basin, so this catches a flip on
        the drill we have seen and may miss one elsewhere". It does miss them,
        demonstrably: excluding `head_twist` flips four of the nine drills at
        the PELVIS by about 31 degrees each, and this line moves by at most
        0.039 across the same change.

        So the shoulder line alone watches one drill and is blind on four.
        THE OTHER HALF WAS NOT BUILT. A pelvis pin was written to be that half
        and withdrawn by its own measurement; the comment beside
        STANCE_DEGREES records why, and this drill's blindness is the cost of
        the withdrawal rather than an oversight. The shoulder line does
        register the mirror, at 0.02 degrees, and even flips sign with it, but
        the tolerance that makes it robust also hides that.

        THE VALUES ARE SIGNED. They were unsigned until 2026-09-02, which meant
        a mirrored pose — same magnitude, opposite sign — would have passed.

        THAT FIX BITES ON ONE DRILL ONLY, and the arithmetic says so. A mirror
        moves this line by twice its recorded value. On `hooks_outside_hand`
        that is 96.4 degrees and the pin catches it. On the other eight it is
        between 0.000 and 0.99 degrees, all BELOW the two-degree tolerance, so
        this pin cannot detect their mirrors however the sign is handled. The
        smallest is `deflect_high`, recorded at -0.000, whose mirror moves this
        line by nothing at all.

        So the sign correction is worth having and it is NOT what makes the
        library covered. Nothing does: the quantity that would cover it, the
        pelvis line, is not pinnable. Refer to the note above PELVIS and to
        "The lower body has no stable solution" in docs/KNOWN_ISSUES.md.
        """
        for movement_id, expected in sorted(STANCE_DEGREES.items()):
            with self.subTest(movement=movement_id):
                self.assertIn(movement_id, self.stance, f"{movement_id} was not solved")
                self.assertAlmostEqual(
                    self.stance[movement_id], expected,
                    delta=STANCE_TOLERANCE_DEGREES,
                    msg=f"{movement_id} now stands "
                        f"{self.stance[movement_id]:.2f} degrees turned against "
                        f"the recorded {expected}. A move of this size is not "
                        "drift. Check whether the solver has changed BASIN on "
                        "that drill before believing anything measured from it, "
                        "and refer to docs/CLAVICLE_ARTEFACT.md.",
                )

    def test_the_pin_covers_every_drill_that_was_solved(self) -> None:
        """Guards the guard. A pin that names fewer drills than the library
        solves would pass while leaving the rest unwatched."""
        missing = sorted(set(self.stance) - set(STANCE_DEGREES))
        self.assertEqual(
            missing, [],
            f"{missing} are solved and not pinned, so a basin flip on them "
            "would go unreported. Add them with their measured stance.",
        )

    def test_a_turned_drill_is_among_them(self) -> None:
        """The anti-hollow clause, RESTORED to the real library.

        The fault only appears on a turned athlete: with square shoulders the
        midpoint is the same distance from both, so the old code was correct by
        accident. A library of square drills passes this file while proving
        nothing.

        THIS CLAUSE WAS INVERTED ON 2026-09-01 AND THAT WAS A MISTAKE, though
        an honest one. `hooks_outside_hand` appeared to have stopped turning —
        48.23 degrees down to 15.44 — and it was recorded as a library-content
        gap, with the contract moved to a hand-built fixture.

        The drill had not changed. It has TWO solved poses about 33 degrees
        apart in ready-stance turn, and which one the solver reaches depends on
        the composition of the enabled parameter set. The set that shipped as
        `ac240b2` was the only one measured that reaches the 15 degree pose.
        Excluding the locked parameters returns her to 48.22 degrees, and so
        does excluding an unrelated axis with a real range. Refer to
        docs/CLAVICLE_ARTEFACT.md.

        The synthetic fixture in `ATurnedAthleteIsStillGuarded` is KEPT. It is
        now belt and braces rather than the only case, and it costs nothing to
        hold a contract in two places when one of them is a library that can
        change.
        """
        self.assertTrue(
            any(degrees > 20.0 for degrees in self.turned.values()),
            "no drill starts turned, so the midpoint and the shoulders agree "
            "and this file cannot see the fault it exists for. Before removing "
            "this clause again, check whether the solver has changed BASIN on "
            "that drill: it has two poses 33 degrees apart, and that is what "
            "happened the last time it read square.",
        )

    def test_the_even_population_is_what_it_claims(self) -> None:
        """Guards the guard. The two below say nothing about an empty set.

        A population read from a flag is only as good as the flag. If
        `movement_carries_no_side` ever narrows, these guards quietly cover
        fewer drills and stay green, so the membership is asserted by name.

        `netball_deflect_high` is named below because it is the drill that
        got in when the flag read one file of the three, and it is the one a
        narrowing would let back.
        """
        even = {name for name, flag in self.even.items() if flag}
        self.assertEqual(
            even,
            set(KNEE_GAP_CEILING_DEGREES),
            "the drills whose authoring is even are not the drills guarded",
        )
        for name in (
            "netball_deflect_high",
            "netball_double_foot_landing",
            "netball_hooks_outside_hand",
            "netball_one_hand_snatch_to_other_hand",
        ):
            self.assertIn(name, self.even, f"{name} was not solved")
            self.assertFalse(
                self.even[name],
                f"{name} authors a side and must not be held to a mirror",
            )

    def test_no_even_drill_solves_more_crookedly_than_it_did(self) -> None:
        """A left-right knee gap that GROWS is a regression nothing else reads.

        The graded checkpoints read each knee against its own band, and both
        knees can drift together inside their bands while the gap between them
        widens. This is the only check that reads the difference.
        """
        for movement_id, ceiling in KNEE_GAP_CEILING_DEGREES.items():
            self.assertIn(movement_id, self.knee_gap, f"{movement_id} not solved")
            self.assertLessEqual(
                self.knee_gap[movement_id],
                ceiling,
                f"{movement_id} now solves {self.knee_gap[movement_id]:.2f} "
                f"degrees crooked, past its recorded {ceiling:.2f}",
            )

    @unittest.expectedFailure
    def test_an_even_drill_solves_evenly(self) -> None:
        """THIS IS EXPECTED TO FAIL TODAY, and the failure is the finding.

        Nothing in these six files distinguishes left from right, so the
        solver should return a mirrored athlete. It returns knees 4.02 to
        6.48 degrees apart on the shipped build. The worst, 6.48 on `hooks_jump_pull_in`, is the
        figure the content lane reported from the other end.

        It is recorded as an EXPECTED failure rather than a comment because
        an expected failure that starts passing is reported as a failure by
        `unittest`. So the day the solver is made to answer evenly, this
        goes red and someone has to come back here, delete it, and write
        down what changed. A comment would have gone on being true forever
        and told nobody.

        A drill whose gap merely SHRINKS does not pass this. Half of 6.48 is
        still not a mirror, and the ceiling guard above is what watches the
        other direction.
        """
        for movement_id in KNEE_GAP_CEILING_DEGREES:
            self.assertLessEqual(
                self.knee_gap[movement_id],
                KNEE_GAP_SOLVED_DEGREES,
                f"{movement_id} solves {self.knee_gap[movement_id]:.2f} "
                "degrees crooked with nothing asking it to",
            )

    def test_no_waiting_hand_is_further_out_than_a_reaching_one(self) -> None:
        """The rule, measured against the library rather than a threshold.

        A hand that is reaching for a ball is the most extended a hand has any
        business being before contact. A hand that is merely waiting must not
        beat it.
        """
        furthest = max(self.reaching.values())
        for (movement_id, side), extension in sorted(self.waiting.items()):
            with self.subTest(movement=movement_id, side=side):
                self.assertLessEqual(
                    extension,
                    furthest,
                    f"{movement_id}: the {side} hand waits at {extension:.3f} of "
                    f"full extension, further out than any hand in the library "
                    f"actually reaching for a ball ({furthest:.3f}). A waiting "
                    "arm is being asked for a point it cannot reach.",
                )

    def test_no_hand_at_all_is_locked_out_before_contact(self) -> None:
        """The blunter statement of the same thing, which survives a library
        where every drill went wrong at once and the comparison above stopped
        discriminating. An elbow at full extension cannot give with a ball."""
        for source in (self.reaching, self.waiting):
            for (movement_id, side), extension in sorted(source.items()):
                with self.subTest(movement=movement_id, side=side):
                    self.assertLess(
                        extension,
                        0.99,
                        f"{movement_id}: the {side} arm reaches {extension:.3f} "
                        "of full extension before she has the ball, which is a "
                        "locked elbow rather than a ready one.",
                    )


class ATurnedAthleteIsStillGuarded(unittest.TestCase):
    """The rule pinned on a hand-built athlete, because the library lost its
    turned drill when the hand was fixed.

    Same pattern as the reference-curve floor: where the real library happens
    not to exercise a contract, the contract is pinned on a fixture rather than
    left unguarded or weakened to fit. A fixture is not authored content and no
    movement definition is touched.

    NO SOLVER. `resolve` is geometry: it is handed shoulders and asked where the
    hands wait. That is the whole rule under test.
    """

    ARM_CM = 52.675
    REACH_LIMIT_CM = 62.0
    HALF_SPAN_CM = 18.0
    TURN_DEGREES = 44.0

    def scene(self, with_places: bool):
        """A steadily turned athlete, and the ball flying at her."""
        import json
        import tempfile
        from pathlib import Path as _Path

        from ball_track import BallOffset, load_ball, stance_frame
        from possession import resolve
        from technique import AfterContactKey

        frames = 40
        phases = [n / (frames - 1) for n in range(frames)]
        chest = np.array([0.0, 130.0, 0.0])
        middle = np.array([0.0, 137.0, 0.0])
        radians = np.radians(self.TURN_DEGREES)
        # Shoulders on a line turned about the vertical. A square athlete puts
        # both the same distance from the midpoint; a turned one does not, and
        # that difference is the entire fault.
        offset = self.HALF_SPAN_CM * np.array(
            [np.cos(radians), 0.0, np.sin(radians)]
        )
        places = [{"l": middle + offset, "r": middle - offset} for _ in phases]

        data = {
            "movementId": "turned-fixture",
            "radiusCm": 11.0,
            "release": {"atPhase": 0.1},
            "arrival": {"atPhase": 0.6},
            "keys": [
                {"atPhase": 0.1, "across": 0.0, "up": 0.3, "ahead": 4.0},
                {"atPhase": 0.35, "across": 0.0, "up": 0.4, "ahead": 2.2},
                {"atPhase": 0.6, "across": 0.0, "up": 0.4, "ahead": 0.9},
            ],
        }
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".ball.json", delete=False, encoding="utf-8"
        )
        json.dump(data, handle)
        handle.close()

        return resolve(
            phases=phases,
            ball=load_ball(_Path(handle.name)),
            stance=stance_frame(chest, self.ARM_CM, 0.0),
            athlete_frames=[
                stance_frame(chest, self.ARM_CM, self.TURN_DEGREES)
                for _ in phases
            ],
            shoulder_mids=[middle for _ in phases],
            shoulder_places=places if with_places else None,
            after_contact=(
                AfterContactKey(0.8, "absorb", BallOffset(0.0, 0.3, 0.6)),
                AfterContactKey(1.0, "pull_in", BallOffset(0.0, 0.1, 0.4)),
            ),
            reach_limit_cm=self.REACH_LIMIT_CM,
            arm_length_cm=self.ARM_CM,
            ready_offset=BallOffset(0.0, 0.2, 0.95),
        ), places

    def worst_reach(self, held, places) -> float:
        """The furthest any shoulder has to stretch to a waiting hand, as a
        fraction of the waiting distance the rule allows."""
        from possession import READY_FRACTION

        allowed = READY_FRACTION * self.REACH_LIMIT_CM
        worst = 0.0
        # WHILE THE PASSER STILL HOLDS THE BALL, which is the only window where
        # she is purely waiting. Once he lets go the hands travel to meet the
        # ball, and a hand reaching for a ball is allowed further out than a
        # hand waiting for one — that distinction is the whole subject of this
        # file, so measuring across both would compare the rule against a case
        # it does not govern.
        for frame in held.frames:
            if frame.state != "held":
                continue
            for place in places[frame.number].values():
                span = float(np.linalg.norm(frame.presented - place))
                worst = max(worst, span / allowed)
        return worst

    def test_the_fixture_is_turned_enough_to_show_the_fault(self) -> None:
        """THE ANTI-HOLLOW CLAUSE FOR THE FIXTURE ITSELF, and without it this
        class proves nothing.

        A fixture that is not turned far enough passes the rule for the same
        reason a square drill does: the midpoint and the shoulders agree. So
        the same scene is run with the correction disabled, and it must FAIL
        there. That is what makes passing with it meaningful.

        It reads 1.340 with the correction off and exactly 1.000 with it on.
        The real drill this replaces put a waiting point 66.4 cm from a
        shoulder against a 50.8 cm waiting distance, which is 1.31, so the
        fixture reproduces the fault at its true size rather than an
        exaggerated one.
        """
        held, places = self.scene(with_places=False)
        worst = self.worst_reach(held, places)
        self.assertGreater(
            worst, 1.0,
            f"with the shoulder correction disabled the furthest shoulder "
            f"still only reaches {worst:.3f} of the waiting distance, so this "
            "fixture is not turned far enough to expose the fault and the "
            "case below passes for the wrong reason",
        )

    def test_no_shoulder_is_asked_past_its_reach_on_a_turned_athlete(
        self,
    ) -> None:
        """The rule. Every shoulder must be able to reach the waiting point."""
        held, places = self.scene(with_places=True)
        worst = self.worst_reach(held, places)
        self.assertLessEqual(
            worst, 1.0 + 1e-9,
            f"a shoulder is asked to stretch {worst:.3f} of the waiting "
            "distance on a turned athlete, so the waiting point is outside "
            "its reach and the arm waits locked out",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
