"""Contract tests for the ball-in-frame annotation.

THE CONDITION MUST BE ABLE TO SAY BOTH THINGS. A gate condition that can only
ever read UNMEASURED is not a condition, and one that can only ever fail is a
wall. Every test below has its opposite: an annotation that blocks and one that
passes, a window that matches and one that has moved, a tristate that is false
and one that is null.

IT ALSO GUARDS THE COMMITTED ANNOTATION ITSELF. `ball-in-frame-0.1.json` is the
only artefact in the video chain a machine cannot rebuild, so it is in the
repository rather than in `poc-output`, and these tests read the real file.
A hand annotation nothing validates is a hand annotation that rots.

No solver, no footage, no OpenCV.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from video_ball_in_frame import (
    NARROW_MARGIN_FRAMES,
    SCHEMA_VERSION,
    WINDOW_TOLERANCE_SECONDS,
    BallAnnotationError,
    annotation_path,
    check_windows,
    judge,
    load_annotation,
)

WINDOWS = [
    (5.267, 5.833), (6.767, 9.367), (9.733, 12.1), (12.1, 12.867),
]


def alignments(windows=WINDOWS) -> list[dict]:
    return [{"window": {"startSeconds": s, "endSeconds": e}} for s, e in windows]


def row(index: int, visible, **extra) -> dict:
    start, end = WINDOWS[index]
    found = {
        "index": index, "startSeconds": start, "endSeconds": end,
        "ballVisible": visible, "evidence": "a frame strip was read",
    }
    found.update(extra)
    return found


def annotation(*rows, **extra) -> dict:
    found = {"schemaVersion": SCHEMA_VERSION, "set": "test",
             "repetitions": list(rows)}
    found.update(extra)
    return found


def write(document: dict) -> Path:
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8")
    handle.write(json.dumps(document))
    handle.close()
    return Path(handle.name)


class ItCanSayBothThings(unittest.TestCase):
    """First and by name. Everything else is detail beside it."""

    def test_all_annotated_and_all_carry_a_ball_PASSES(self):
        found = judge(annotation(*(row(n, True) for n in range(4))), alignments())

        self.assertIs(found["passes"], True)
        self.assertEqual(found["withoutBall"], [])
        self.assertEqual(found["notLookedAt"], [])

    def test_one_repetition_without_a_ball_FAILS_and_names_it(self):
        found = judge(
            annotation(row(0, False), *(row(n, True) for n in (1, 2, 3))),
            alignments())

        self.assertIs(found["passes"], False)
        self.assertEqual(found["withoutBall"], [0])
        self.assertIn("NO BALL IN FRAME", found["detail"])
        self.assertIn("0", found["detail"])


class UnmeasuredIsNotAPass(unittest.TestCase):
    def test_no_annotation_at_all_is_unmeasured(self):
        found = judge(None, alignments())

        self.assertIsNone(found["passes"])
        self.assertEqual(found["notLookedAt"], [0, 1, 2, 3])
        self.assertEqual(found["withBall"], [],
                         "a list on every path, never an int")

    def test_a_repetition_nobody_looked_at_is_unmeasured(self):
        found = judge(
            annotation(row(0, True), row(1, None), row(2, True), row(3, True)),
            alignments())

        self.assertIsNone(found["passes"])
        self.assertEqual(found["notLookedAt"], [1])
        self.assertIn("not looked at is not", found["detail"].lower())

    def test_a_repetition_left_out_of_the_file_is_unmeasured_too(self):
        """Absent from the annotation is absent from the looking. Only judging
        the rows present would let a two-row file about a twelve-repetition
        clip report a clean pass."""
        found = judge(annotation(row(0, True), row(1, True)), alignments())

        self.assertIsNone(found["passes"])
        self.assertEqual(found["notLookedAt"], [2, 3])

    def test_a_false_beats_a_null_when_both_are_present(self):
        """A known gesture is worse news than an unlooked repetition, and the
        verdict must lead with the thing that is known."""
        found = judge(annotation(row(0, False), row(1, None)), alignments())

        self.assertIs(found["passes"], False)


class CauseAndMarginTest(unittest.TestCase):
    """What the gate SAYS, not only what it decides.

    A count of three is not actionable. Two of those three need a slate and one
    needs different framing, and two of the nine passes rest on a single frame.
    A verdict that hid either would send a reader to the annotation to find out
    what to do.
    """

    def test_the_cause_is_named_per_repetition_in_the_detail(self):
        found = judge(annotation(
            row(0, False, cause="gesture"), row(1, False, cause="framing"),
            row(2, True), row(3, True)), alignments())

        self.assertIn("0 (gesture)", found["detail"])
        self.assertIn("1 (framing)", found["detail"])
        self.assertEqual(found["causes"], {0: "gesture", 1: "framing"})

    def test_a_cause_that_is_not_one_of_the_two_is_refused(self):
        path = write(annotation(row(0, False, cause="dunno")))
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        with self.assertRaises(BallAnnotationError) as raised:
            load_annotation(path)
        self.assertIn("different shoot instructions", str(raised.exception))

    def test_a_thin_pass_is_reported_with_ITS_OWN_margin(self):
        """The reading, never the threshold it fell under."""
        found = judge(annotation(
            row(0, True, marginFrames=1), row(1, True, marginFrames=2),
            row(2, True, marginFrames=9), row(3, True)), alignments())

        self.assertIs(found["passes"], True)
        self.assertEqual(found["narrowPasses"], [0, 1])
        self.assertIn("0 (1 frame), 1 (2 frames)", found["detail"])
        self.assertNotIn("2 (9 frames)", found["detail"])

    def test_a_wide_pass_is_not_called_narrow(self):
        found = judge(annotation(*(row(n, True, marginFrames=9)
                                   for n in range(4))), alignments())

        self.assertEqual(found["narrowPasses"], [])
        self.assertNotIn("NARROW", found["detail"])

    def test_an_uncounted_margin_is_not_treated_as_wide(self):
        """Null means nobody counted it, which is not the same as clear."""
        found = judge(annotation(*(row(n, True) for n in range(4))), alignments())

        self.assertEqual(found["narrowPasses"], [])
        for row_ in found["withBall"]:
            self.assertIn(row_, [0, 1, 2, 3])

    def test_a_negative_margin_is_refused(self):
        path = write(annotation(row(0, True, marginFrames=-1)))
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        with self.assertRaises(BallAnnotationError):
            load_annotation(path)

    def test_the_narrow_bar_is_the_anchors_own_localisation(self):
        self.assertEqual(NARROW_MARGIN_FRAMES, 2)


class StaleAnnotationsAreRefused(unittest.TestCase):
    def test_a_matching_window_is_accepted(self):
        check_windows(annotation(row(0, True)), alignments())

    def test_a_window_inside_the_tolerance_is_accepted(self):
        """A tooling change that nudges an onset by a frame is not a new
        repetition."""
        moved = list(WINDOWS)
        moved[0] = (WINDOWS[0][0] + WINDOW_TOLERANCE_SECONDS * 0.9, WINDOWS[0][1])

        check_windows(annotation(row(0, True)), alignments(moved))

    def test_a_window_that_moved_refuses_the_WHOLE_file(self):
        """Not the row. A half-stale annotation is one nobody can tell the
        halves apart in."""
        moved = list(WINDOWS)
        moved[0] = (WINDOWS[0][0] + 1.0, WINDOWS[0][1])

        with self.assertRaises(BallAnnotationError) as raised:
            check_windows(annotation(row(0, True), row(1, True)), alignments(moved))
        self.assertIn("stale", str(raised.exception))
        self.assertIn("none of it is used", str(raised.exception))

    def test_an_annotation_longer_than_the_alignment_is_refused(self):
        with self.assertRaises(BallAnnotationError) as raised:
            check_windows(annotation(row(3, True)), alignments(WINDOWS[:2]))
        self.assertIn("tooling has changed", str(raised.exception))

    def test_judge_refuses_a_stale_file_rather_than_scoring_it(self):
        moved = list(WINDOWS)
        moved[0] = (WINDOWS[0][0] + 1.0, WINDOWS[0][1])

        with self.assertRaises(BallAnnotationError):
            judge(annotation(row(0, False)), alignments(moved))


class TheFileFormatRefusesWhatItCannotTrust(unittest.TestCase):
    def setUp(self):
        self.paths: list[Path] = []
        self.addCleanup(lambda: [p.unlink(missing_ok=True) for p in self.paths])

    def save(self, document: dict) -> Path:
        path = write(document)
        self.paths.append(path)
        return path

    def test_a_good_file_loads(self):
        found = load_annotation(self.save(annotation(row(0, True))))

        self.assertEqual(found["schemaVersion"], SCHEMA_VERSION)

    def test_a_missing_file_is_None_and_not_an_error(self):
        self.assertIsNone(load_annotation(Path("no-such-annotation.json")))

    def test_a_wrong_schema_version_is_refused(self):
        document = annotation(row(0, True))
        document["schemaVersion"] = "ball-in-frame-0"

        with self.assertRaises(BallAnnotationError):
            load_annotation(self.save(document))

    def test_an_annotation_without_evidence_is_refused(self):
        """An annotation without evidence is an opinion."""
        bad = row(0, True)
        del bad["evidence"]

        with self.assertRaises(BallAnnotationError) as raised:
            load_annotation(self.save(annotation(bad)))
        self.assertIn("evidence", str(raised.exception))

    def test_an_annotation_without_its_window_is_refused(self):
        """The window is what makes a stale file detectable."""
        bad = row(0, True)
        del bad["startSeconds"]

        with self.assertRaises(BallAnnotationError):
            load_annotation(self.save(annotation(bad)))

    def test_a_value_that_is_not_the_tristate_is_refused(self):
        with self.assertRaises(BallAnnotationError) as raised:
            load_annotation(self.save(annotation(row(0, "yes"))))
        self.assertIn("null is not", str(raised.exception).lower())

    def test_the_throughout_field_is_tristate_too(self):
        with self.assertRaises(BallAnnotationError):
            load_annotation(
                self.save(annotation(row(0, True, ballVisibleThroughout="mostly"))))

    def test_the_throughout_field_is_optional(self):
        """An annotator who only watched the catch must not be made to guess
        about the lead."""
        found = load_annotation(self.save(annotation(row(0, True))))

        self.assertNotIn("ballVisibleThroughout", found["repetitions"][0])

    def test_one_repetition_annotated_twice_is_refused(self):
        with self.assertRaises(BallAnnotationError) as raised:
            load_annotation(self.save(annotation(row(0, True), row(0, False))))
        self.assertIn("twice", str(raised.exception))


class TheCommittedAnnotationForSessionOne(unittest.TestCase):
    """The real file, in the repository. A hand annotation nothing validates
    is a hand annotation that rots."""

    def setUp(self):
        self.path = annotation_path("0.1")
        if not self.path.exists():
            self.skipTest(f"{self.path} is not present")
        self.document = load_annotation(self.path)

    def test_it_loads_and_validates(self):
        self.assertEqual(self.document["schemaVersion"], SCHEMA_VERSION)
        self.assertEqual(len(self.document["repetitions"]), 12)

    def test_the_two_no_ball_causes_are_distinguished_in_the_evidence(self):
        """THREE repetitions have no ball at the anchor and for TWO reasons.
        A gate that recorded only the count would lose the distinction, and
        the two need different shoot instructions."""
        rows = {r["index"]: r["evidence"] for r in self.document["repetitions"]}

        self.assertIn("gesturing", rows[0])
        self.assertIn("NO BALL ANYWHERE", rows[8])
        self.assertIn("leaves the TOP of the frame", rows[2])
        self.assertIn("not a gesture", rows[2])

    def test_the_two_gestures_are_named_as_the_sync_claps(self):
        """Identified 2026-09-04. Repetitions 0 and 8 are Erin's sync claps,
        and repetition 0 is the one that scored best of twelve. A row that
        knows what it is is worth more than a row that knows what it is not."""
        rows = {r["index"]: r["evidence"] for r in self.document["repetitions"]}

        for index in (0, 8):
            self.assertIn("SYNC CLAP", rows[index])
        self.assertIn("5.800", rows[0])
        self.assertIn("17.835", rows[8])
        self.assertIn("0.02369", self.document["note"])

    def test_no_prose_in_this_file_can_move_a_verdict(self):
        """THE ANNOTATION IS DATA THE GATE READS, so an edit to it has to be
        provably inert. `judge` reads index, ballVisible, cause and
        marginFrames and nothing else; every other field is for a person.

        This mutates EVERY prose field — the per-row evidence and all six
        top-level notes — and requires the verdict to come back identical. A
        version that started reading the evidence, or that folded a note into
        the detail line, fails here rather than in a coach's report."""
        import copy

        rows = sorted(self.document["repetitions"], key=lambda r: r["index"])
        windows = [{"window": {"startSeconds": r["startSeconds"],
                               "endSeconds": r["endSeconds"]}} for r in rows]
        before = judge(self.document, windows)

        mutated = copy.deepcopy(self.document)
        for row in mutated["repetitions"]:
            row["evidence"] = "MUTATED, and no verdict may notice."
        for field in ("annotatedBy", "method", "note", "seekWarning",
                      "marginNote", "causeNote"):
            if field in mutated:
                mutated[field] = "MUTATED, and no verdict may notice."
        after = judge(mutated, windows)

        self.assertEqual(before, after)

    def test_the_causes_are_recorded_for_every_blocking_row(self):
        rows = {r["index"]: r for r in self.document["repetitions"]}

        self.assertEqual(rows[0]["cause"], "gesture")
        self.assertEqual(rows[2]["cause"], "framing")
        self.assertEqual(rows[8]["cause"], "gesture")

    def test_the_two_one_frame_passes_carry_their_margin(self):
        """Repetitions 5 and 7 each carry a ball in exactly one frame of their
        anchored span. Presented as plain passes they would read as clear."""
        rows = {r["index"]: r for r in self.document["repetitions"]}

        self.assertEqual(rows[5]["marginFrames"], 1)
        self.assertEqual(rows[7]["marginFrames"], 1)

    def test_the_resampled_timestamp_is_withdrawn_rather_than_deleted(self):
        """14.875 was an fps-resampled OUTPUT value, not a front-camera PTS —
        the front runs at exactly 30.000 fps, so its frames here are 14.833,
        14.867 and 14.900.

        THE ROW QUOTES THE WITHDRAWN CLAIM RATHER THAN ERASING IT, which is why
        this test does not assert the old string's absence: a first version did,
        and failed on the quotation that does the withdrawing. Someone who read
        the earlier figure elsewhere needs to find out here that it was wrong,
        and a silent deletion tells them nothing.
        """
        evidence = {r["index"]: r["evidence"] for r in self.document["repetitions"]}

        self.assertIn("14.900", evidence[5])
        self.assertIn("RESAMPLED", evidence[5])
        self.assertIn("An earlier version of this row said", evidence[5])
        self.assertIn("ONE FRAME", evidence[5])
        # the withdrawn figure appears only inside the sentence that withdraws it
        self.assertLess(evidence[5].index("An earlier version"),
                        evidence[5].index("25 ms to spare"))

    def test_the_keyframe_caution_is_recorded(self):
        """Three keyframes in the side file against one a second in the front.
        A snapping reader asked for 16.93 lands at 9.996, which is where
        repetition 2's catch lives — the original symptom, explained."""
        warning = self.document["seekWarning"]

        self.assertIn("THREE", warning)
        self.assertIn("9.996", warning)
        self.assertIn("KEYFRAME-SNAPPING", warning)

    def test_it_records_the_repetition_this_whole_condition_exists_for(self):
        first = self.document["repetitions"][0]

        self.assertEqual(first["index"], 0)
        self.assertIs(first["ballVisible"], False)
        self.assertIn("NO BALL IS PRESENT", first["evidence"])

    def test_nothing_is_left_unlooked_at(self):
        """The four rejected on RANKING alone have now been watched. While
        they were null they were correctly null — inferring a ball from a
        rejection that never mentioned one would have been fabrication."""
        unlooked = [r["index"] for r in self.document["repetitions"]
                    if r["ballVisible"] is None]

        self.assertEqual(unlooked, [])

    def test_it_says_which_rows_are_transcribed_and_which_are_a_fresh_look(self):
        """Two kinds of row with different authority, and a reader must be able
        to tell them apart without knowing the history."""
        self.assertIn("TWO KINDS OF ROW", self.document["method"])
        self.assertIn("TRANSCRIBED", self.document["method"])
        self.assertIn("FRESH LOOK", self.document["method"])

        fresh = [r["index"] for r in self.document["repetitions"]
                 if "A FRESH LOOK" in r["evidence"]]
        self.assertEqual(fresh, [2, 5, 7, 8])

    def test_the_seek_warning_withdraws_the_blame_it_first_carried(self):
        """A first version blamed fast seek and that blame was not supported:
        three seek methods return the identical frame. The field now names what
        IS established — a fixed-offset label inside a resampling chain — and
        says the earlier claim was withdrawn, because a warning that impugns a
        sound method is worse than none."""
        warning = self.document["seekWarning"]

        self.assertIn("WITHDRAWN AND REPLACED", warning)
        self.assertIn("NOT SUPPORTED", warning)
        self.assertIn("FIXED OFFSET", warning)
        self.assertIn("MATCH THE FRAME BACK", warning)

    def test_it_carries_the_build_its_windows_came_from(self):
        source = self.document["windowSource"]

        self.assertTrue(source["commit"].startswith("bb7dc4c"))
        self.assertIs(source["treeWasClean"], True)

    def test_every_row_carries_evidence(self):
        for found in self.document["repetitions"]:
            self.assertTrue(found["evidence"].strip(), found["index"])

    def test_it_blocks_the_gate_on_its_own_windows(self):
        """The end to end reading: this annotation, against the windows it
        names, must fail and must name repetition 0."""
        windows = [
            {"window": {"startSeconds": r["startSeconds"],
                        "endSeconds": r["endSeconds"]}}
            for r in self.document["repetitions"]
        ]

        found = judge(self.document, windows)

        self.assertIs(found["passes"], False)
        self.assertEqual(found["withoutBall"], [0, 2, 8])
        self.assertEqual(found["withBall"], [1, 3, 4, 5, 6, 7, 9, 10, 11])
        self.assertEqual(found["notLookedAt"], [])


if __name__ == "__main__":
    unittest.main()
