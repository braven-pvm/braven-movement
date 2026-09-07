"""Tests for the event ledger and its fit test.

THE PASSING BRANCH IS TESTED FIRST AND BY NAME, because this instrument exists
to replace two that could only ever agree with whoever ran them. A genuine pair
must be recognised, or "not a synchronous pair" means nothing.

AND THE FIT TEST'S OWN FIRST VERSION WAS AS WEAK AS THE OFFSETS IT JUDGED. It
asked only for two matched anchors ten seconds apart. Measured on session 0.1, a
RANDOMLY GENERATED side ledger satisfies that 43.2 per cent of the time at
one-frame tolerance and 83.2 per cent at a quarter second, measured by
`anchor_rule_null_rate` at 500 trials and seed 0 and pinned below. (This said
48 and 88 until 2026-09-07; those came from a scratch script nobody could run.) The rule now has to
beat its own null, and the test below pins that.
"""

from __future__ import annotations

import json
import unittest

from video_event_ledger import (
    anchor_rule_null_rate,
    pairing_drift,
    ANCHOR_GAP_SECONDS,
    KINDS,
    NULL_PERCENTILE,
    SCHEMA_VERSION,
    TOLERANCE_SECONDS,
    events,
    fits_one_offset,
    judge,
    load,
    null_matches,
)


def ledger(front, side, set_id="test"):
    def rows(pairs):
        return [{"frameIndex": int(t * 30), "seconds": t, "kind": k}
                for t, k in pairs]
    return {"schemaVersion": SCHEMA_VERSION, "set": set_id,
            "views": {"front": {"events": rows(front)},
                      "side": {"events": rows(side)}}}


class AGenuinePairIsRecognised(unittest.TestCase):
    """The reachable pass. Without it, every refusal below proves nothing."""

    def pair(self, offset=0.8, jitter=0.0):
        beats = [2.0, 4.1, 6.3, 9.0, 12.4, 15.1, 18.6, 21.0, 24.3]
        front = [(t, "catch") for t in beats]
        side = [(round(t + offset + (jitter if n % 2 else -jitter), 4), "catch")
                for n, t in enumerate(beats)]
        return front, side

    def test_one_offset_is_found_and_beats_chance(self):
        front, side = self.pair(offset=0.8)

        found = fits_one_offset(*(events(ledger(front, side), v)
                                  for v in ("front", "side")))

        self.assertTrue(found["fits"], found["why"])
        self.assertAlmostEqual(found["bestOffsetSeconds"], 0.8, delta=0.02)
        self.assertGreater(found["matchedEvents"], found["nullPercentileMatches"])

    def test_it_survives_a_frame_of_reading_error_on_each_event(self):
        # Two people calling the same event can each be a frame out.
        front, side = self.pair(offset=0.8, jitter=0.016)

        found = fits_one_offset(*(events(ledger(front, side), v)
                                  for v in ("front", "side")))

        self.assertTrue(found["fits"], found["why"])

    def test_the_span_is_the_span_of_the_matched_events(self):
        front, side = self.pair(offset=0.8)

        found = fits_one_offset(*(events(ledger(front, side), v)
                                  for v in ("front", "side")))

        self.assertGreaterEqual(found["spanSeconds"], ANCHOR_GAP_SECONDS)


class TwoAnchorsAreNotEnoughOnTheirOwn(unittest.TestCase):
    """The fault this module's own first version had."""

    def test_a_pair_matching_only_at_its_ends_does_not_pass(self):
        # Two events that line up 20 s apart and nothing in between. The
        # anchor rule alone accepts this; the null does not, because two
        # matches out of many is what chance produces.
        front = [(t, "catch") for t in (2.0, 5.0, 8.0, 11.0, 14.0, 17.0, 22.0)]
        side = [(2.5, "catch"), (6.3, "catch"), (9.1, "catch"),
                (13.7, "catch"), (16.2, "catch"), (19.4, "catch"),
                (22.5, "catch")]

        found = fits_one_offset(*(events(ledger(front, side), v)
                                  for v in ("front", "side")))

        self.assertLessEqual(found["matchedEvents"],
                             found["nullPercentileMatches"] + 1)

    def test_the_null_is_reported_with_every_answer(self):
        front, side = [(2.0, "catch"), (12.0, "catch")], [(2.5, "catch")]

        found = fits_one_offset(*(events(ledger(front, side), v)
                                  for v in ("front", "side")))

        self.assertIn("nullPercentileMatches", found)
        self.assertIn("nullTrials", found)

    def test_a_count_EQUAL_to_the_chance_ceiling_does_not_fit(self):
        """`count > bar` MUST NOT BECOME `count >= bar`, and until this test
        existed the change passed all sixteen. Session 0.1 at a quarter second
        is the case: it explains SIX events against a ceiling of SIX. Reading
        that as a fit accepts a pairing of two files that are not a pair."""
        found = load("0.1")
        if found is None:
            self.skipTest("event-ledger-0.1.json is not present")

        r = fits_one_offset(events(found, "front"), events(found, "side"),
                            tolerance=0.267)

        self.assertEqual(r["matchedEvents"], r["nullPercentileMatches"],
                         "the fixture must sit exactly ON the ceiling")
        self.assertFalse(r["fits"], "equal to chance is not better than chance")

    def test_events_crowded_into_a_few_seconds_do_not_fit(self):
        """THE ANCHOR RULE MUST NOT BE REMOVED, and until this test existed
        removing it passed all sixteen. Eight events matching perfectly inside
        4 s beat chance easily and say nothing: a wrong offset only has to
        survive one stretch of a periodic movement to look like this."""
        beats = [2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5]
        front = [(t, "catch") for t in beats]
        side = [(t + 0.8, "catch") for t in beats]

        found = fits_one_offset(*(events(ledger(front, side), v)
                                  for v in ("front", "side")))

        self.assertGreater(found["matchedEvents"], found["nullPercentileMatches"])
        self.assertLess(found["spanSeconds"], ANCHOR_GAP_SECONDS)
        self.assertFalse(found["fits"], "beating chance inside 4 s is not a sync")

    def test_the_null_grows_as_the_tolerance_is_relaxed(self):
        # The reason a loose tolerance cannot rescue a bad ledger: chance
        # rises with it, so the bar rises too.
        front = [(t, "catch") for t in (2.0, 5.0, 8.0, 11.0, 14.0, 17.0, 20.0)]
        side = [(t, "catch") for t in (2.4, 6.1, 9.3, 12.2, 15.8, 18.1, 21.4)]
        f, s = events(ledger(front, side), "front"), events(ledger(front, side), "side")

        tight = max(null_matches(f, s, 1 / 30, trials=100))
        loose = max(null_matches(f, s, 0.5, trials=100))

        self.assertLess(tight, loose)


class SilenceIsNotConsent(unittest.TestCase):

    def test_no_ledger_is_unmeasured_rather_than_a_refusal(self):
        passes, why = judge(None)

        self.assertIsNone(passes)
        self.assertIn("no event ledger", why)

    def test_a_ledger_of_the_wrong_schema_is_unmeasured(self):
        stale = ledger([(1.0, "catch")], [(1.0, "catch")])
        stale["schemaVersion"] = "something-else"

        self.assertIsNone(judge(stale)[0])

    def test_an_empty_ledger_does_not_fit(self):
        found = fits_one_offset([], [])

        self.assertFalse(found["fits"])

    def test_a_catch_is_never_matched_to_a_clap(self):
        """The vocabulary is closed so a fit compares like with like."""
        front = [(t, "catch") for t in (2.0, 6.0, 10.0, 14.0, 18.0)]
        side = [(t + 0.5, "clap") for t in (2.0, 6.0, 10.0, 14.0, 18.0)]

        found = fits_one_offset(*(events(ledger(front, side), v)
                                  for v in ("front", "side")))

        self.assertFalse(found["fits"])

    def test_the_kinds_are_the_declared_vocabulary(self):
        self.assertEqual(KINDS, ("catch", "release", "clap"))


class TheCommittedLedgers(unittest.TestCase):
    """The real readings, as a consumer meets them."""

    def test_set_one_is_read_and_is_not_a_synchronous_pair(self):
        found = load("0.1")
        if found is None:
            self.skipTest("event-ledger-0.1.json is not present")

        self.assertIn("NOT A SYNCHRONOUS PAIR", found["verdict"])
        self.assertIs(judge(found)[0], False)

    def test_set_one_records_WHY_it_is_not_a_pair(self):
        """The ledger found the negative; the frames found the cause. A ledger
        that says "no offset fits" without saying that the FILE NAMES ARE WRONG
        leaves the next reader to rediscover it."""
        found = load("0.1")
        if found is None:
            self.skipTest("event-ledger-0.1.json is not present")

        self.assertIn("FILE NAMES ARE WRONG", found["why"])
        self.assertIn("side 0.2.mp4", found["why"])

    def test_set_one_records_the_sequence_that_settles_it(self):
        """The arithmetic is not the evidence, the sequence is: the front
        stands empty-handed from 17.3 to 20.0 s, and no empty stretch in
        `side 0.1.mp4` after 8.26 s lasts much over a second."""
        found = load("0.1")
        if found is None:
            self.skipTest("event-ledger-0.1.json is not present")

        self.assertIn("17.3", found["why"])
        # NOT "continuously". That word was in an earlier version of the side
        # note and the contact sheet refutes it: she releases about 17.5 and
        # her hands are empty 17.59 to 18.39. What settles it is the LENGTH of
        # the longest empty stretch in each view.
        self.assertIn("NO EMPTY STRETCH IN THIS VIEW",
                      found["views"]["side"]["note"])
        self.assertIn("2.7 s", found["views"]["side"]["note"])

    def test_the_refuted_word_survives_nowhere_in_the_ledger(self):
        """IT WAS CORRECTED IN ONE PLACE OF FIVE AND THE COMMIT SAID IT WAS
        RESTATED. The side note was rewritten; the file's own top-level `why`
        still said "handles a ball continuously", and so did two places in
        VIDEO_CAPTURE_FINDINGS.md and one in HANDOFF_RENDERING.md. A claim is
        withdrawn where it is written, not where it is most convenient."""
        found = load("0.1")
        if found is None:
            self.skipTest("event-ledger-0.1.json is not present")

        for where in ("why", ):
            with self.subTest(field=where):
                said = found[where]
                marked = said[said.index("used to say"):] if "used to say" in said else ""
                live = said.replace(marked, "")

                self.assertNotIn("continuously", live.lower(),
                                 "the refuted word survives unmarked")

    def test_set_one_carries_the_fit_sweep_and_its_chance_ceiling(self):
        found = load("0.1")
        if found is None:
            self.skipTest("event-ledger-0.1.json is not present")

        for row in found["fitSweep"]:
            self.assertIn("chanceCeiling", row)
        self.assertTrue(any(r["toleranceSeconds"] == round(TOLERANCE_SECONDS, 4)
                            for r in found["fitSweep"]))

    def test_set_two_is_recorded_as_UNREAD_rather_than_guessed(self):
        """A ledger read at a confidence the frames cannot support would be
        worse than none: it is the input to a fit test, and unreliable inputs
        are how -0.7295 was published."""
        found = load("0.2")
        if found is None:
            self.skipTest("event-ledger-0.2.json is not present")

        self.assertEqual(found["verdict"], "NOT READ")
        self.assertEqual(found["views"]["front"]["events"], [])
        self.assertIsNone(found["fit"]["fits"])
        self.assertIn("cannot be told", found["method"])

    def test_the_percentile_is_the_named_constant(self):
        self.assertEqual(NULL_PERCENTILE, 99)


class ThePairingDriftIsAnArtefactOfTheCountMismatch(unittest.TestCase):
    """The three rates a review asked for, produced by committed code.

    They were quoted as +12.6, +16.0 and +13.7 per cent and lived in a scratch
    log. The sign is a convention (side minus front here), the magnitudes are
    the point: the clocks differ by 0.04 per cent, so a rate a hundred times
    larger is not a rate."""

    def setUp(self):
        self.ledger = load("0.1")
        if self.ledger is None:
            self.skipTest("event-ledger-0.1.json is not present")
        self.front = events(self.ledger, "front", "catch")
        self.side = events(self.ledger, "side", "catch")

    def test_the_counts_that_cause_it(self):
        """8 against 10 over roughly one span. That IS the mechanism."""
        self.assertEqual(len(self.front), 8)
        self.assertEqual(len(self.side), 10)

    def test_the_three_rates(self):
        for shift, rate in ((0, -16.0), (1, -13.7), (2, -12.6)):
            with self.subTest(shift=shift):
                found = pairing_drift(self.front, self.side, shift)

                self.assertEqual(found["ratePerCent"], rate)
                self.assertEqual(found["pairs"], 8)

    def test_every_rate_is_orders_larger_than_the_clocks_can_explain(self):
        """The clocks differ by about 0.04 per cent. Anything near 1 per cent
        would already be unexplainable; these are above 12."""
        for shift in (0, 1, 2):
            with self.subTest(shift=shift):
                found = pairing_drift(self.front, self.side, shift)

                self.assertGreater(abs(found["ratePerCent"]), 10.0)

    def test_two_sequences_of_equal_length_and_spacing_drift_by_nothing(self):
        """The control. If this also drifted, the arithmetic would be the
        cause rather than the count mismatch."""
        front = [{"seconds": 1.0 + 2.0 * i} for i in range(8)]
        side = [{"seconds": 1.5 + 2.0 * i} for i in range(8)]

        found = pairing_drift(front, side, 0)

        self.assertEqual(found["ratePerCent"], 0.0)

    def test_a_shift_that_leaves_fewer_than_two_pairs_returns_nothing(self):
        self.assertIsNone(pairing_drift(self.front, self.side, 99))


class TheQuotedNullRateIsProducedByCommittedCode(unittest.TestCase):
    """THE FIGURES WERE QUOTED WITHOUT AN INSTRUMENT, TWICE, AND WERE WRONG
    BOTH TIMES: 48 and 88 from a scratch script that no longer exists, then 43
    and 85 naming two functions that do not compute the quantity. These run
    `anchor_rule_null_rate` and pin what it actually returns."""

    def setUp(self):
        self.ledger = load("0.1")
        if self.ledger is None:
            self.skipTest("event-ledger-0.1.json is not present")
        self.front = events(self.ledger, "front")
        self.side = events(self.ledger, "side")

    def test_at_one_frame_the_anchor_rule_alone_is_satisfied_43_2_per_cent(self):
        found = anchor_rule_null_rate(self.front, self.side,
                                      tolerance=TOLERANCE_SECONDS)

        self.assertAlmostEqual(found, 0.432, places=3)

    def test_at_a_quarter_second_it_is_83_2_per_cent(self):
        found = anchor_rule_null_rate(self.front, self.side, tolerance=0.25)

        self.assertAlmostEqual(found, 0.832, places=3)

    def test_a_wider_tolerance_can_never_lower_the_rate(self):
        """A property, not a pinned figure: the rate must be monotone in the
        tolerance. A pinned pair alone cannot tell a real measurement from a
        constant."""
        rates = [anchor_rule_null_rate(self.front, self.side, tolerance=t)
                 for t in (TOLERANCE_SECONDS, 0.1, 0.25)]

        self.assertEqual(rates, sorted(rates))

    def test_the_rate_is_the_same_on_a_second_run_with_the_same_seed(self):
        """Re-runnable is the whole point of committing it."""
        a = anchor_rule_null_rate(self.front, self.side, trials=100, seed=7)
        b = anchor_rule_null_rate(self.front, self.side, trials=100, seed=7)

        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
