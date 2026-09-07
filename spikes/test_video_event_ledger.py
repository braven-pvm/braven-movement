"""Tests for the event ledger and its fit test.

THE PASSING BRANCH IS TESTED FIRST AND BY NAME, because this instrument exists
to replace two that could only ever agree with whoever ran them. A genuine pair
must be recognised, or "not a synchronous pair" means nothing.

AND THE FIT TEST'S OWN FIRST VERSION WAS AS WEAK AS THE OFFSETS IT JUDGED. It
asked only for two matched anchors ten seconds apart. Measured on session 0.1, a
RANDOMLY GENERATED side ledger satisfies that 48 per cent of the time at
one-frame tolerance and 88 per cent at a quarter second. The rule now has to
beat its own null, and the test below pins that.
"""

from __future__ import annotations

import json
import unittest

from video_event_ledger import (
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

        self.assertEqual(found["verdict"], "NOT A SYNCHRONOUS PAIR")
        self.assertIs(judge(found)[0], False)

    def test_set_one_records_the_sequence_that_settles_it(self):
        """The arithmetic is not the evidence. The front stands empty-handed
        from 17.3 to 20.0 s while the side handles a ball throughout, and no
        offset reconciles a pause with continuous play."""
        found = load("0.1")
        if found is None:
            self.skipTest("event-ledger-0.1.json is not present")

        self.assertIn("17.3", found["why"])
        self.assertIn("continuously", found["views"]["side"]["note"])

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


if __name__ == "__main__":
    unittest.main()
