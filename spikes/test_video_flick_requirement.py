"""The shoot requirement, and the document that quotes it.

THE REQUIREMENT TESTS NEED NO ARTEFACT OUTSIDE GIT, so they run on the hosted
runner rather than skipping: the input is a measurement recorded in the
document on 2026-09-02, not a file. The SCATTER tests need the keypoints and
skip by name without them, which is the honest split — a reported measurement
cannot be checked where the recording is absent.

Every figure published in the document's section is checked here, not only the
table. A section whose prose carries a number no test reads is how the last
two withdrawals happened.
"""

from __future__ import annotations

import re
import unittest
import unittest.mock as mock

import video_flick_requirement as req

FILMING_GUIDE = req.SPIKE_DIR.parent / "docs" / "FILMING_GUIDE.md"
SECTION = "### Re-measured 2026-09-08, and the hundred pixels stands"


def findings_text() -> str:
    return req.FINDINGS.read_text(encoding="utf-8")


def section_text() -> str:
    text = findings_text()
    start = text.index(SECTION)
    return text[start:text.index("\n**Instruction:", start)]


def keypoints_present() -> bool:
    return all(req.speed.keypoint_path(w.view, w.setId).exists()
               for w in req.SCATTER_WINDOWS)


class TheRequirementRestsOnAMeasuredFloor(unittest.TestCase):

    def test_the_floor_is_the_2026_09_02_reading_and_the_document_says_so(self):
        text = findings_text()
        for field, value in zip(("median", "p90", "maximum"),
                                (req.MEASURED_FLOOR.median,
                                 req.MEASURED_FLOOR.p90,
                                 req.MEASURED_FLOOR.maximum)):
            with self.subTest(field=field):
                self.assertIn(f"**{value:.0f}", text)

    def test_the_floor_scales_with_the_lever_and_is_solved_not_typed(self):
        """Twice the lever, half the floor. If `floor_at` answered the same
        whatever it was given, every lever below would be arithmetic about
        nothing."""
        here = req.floor_at(req.MEASURED_FLOOR.leverPixels)
        far = req.floor_at(2 * req.MEASURED_FLOOR.leverPixels)

        self.assertAlmostEqual(here, req.MEASURED_FLOOR.maximum)
        self.assertAlmostEqual(far, req.MEASURED_FLOOR.maximum / 2)

    def test_the_lever_and_the_floor_are_the_same_arithmetic(self):
        """`lever_for` must be the inverse of `floor_at`: at the lever it
        returns, the floor is exactly a third of the flick's rate."""
        for flick in req.ASSUMED:
            with self.subTest(flick=flick):
                lever = req.lever_for(flick)

                self.assertAlmostEqual(req.floor_at(lever) * req.MARGIN,
                                       req.flick_rate(flick))

    def test_the_published_lever_is_the_strictest_never_an_average(self):
        every = [req.lever_for(f) for f in req.ASSUMED]

        self.assertAlmostEqual(req.published_lever(), max(every))
        self.assertGreater(req.published_lever(), sum(every) / len(every))

    def test_the_published_lever_is_taken_against_the_MAXIMUM(self):
        """The conservative row. Publishing the median would ask for a fifth
        of the pixels and would be defensible arithmetic on the wrong
        statistic.

        The strictest lever comes from the SLOWEST flick, because the lever
        falls as the rate rises. I had this backwards and the test caught it.
        """
        strictest = min(req.ASSUMED, key=req.flick_rate)

        self.assertAlmostEqual(req.published_lever(),
                               req.lever_for(strictest, "maximum"))
        self.assertGreater(req.lever_for(strictest, "maximum"),
                           req.lever_for(strictest, "p90"))
        self.assertGreater(req.lever_for(strictest, "p90"),
                           req.lever_for(strictest, "median"))

    def test_the_hundred_pixels_of_2026_09_02_sits_above_the_requirement(self):
        """It stands because it clears the strictest lever, not because it is
        older."""
        self.assertLess(req.published_lever(), 100.0)

    def test_pixels_are_not_enough_and_the_frame_rate_is_separate(self):
        for flick in req.ASSUMED:
            with self.subTest(flick=flick):
                self.assertGreater(req.frames_per_second_for(flick),
                                   req.SHOT_AT_FPS)


class TheRequirementDoesNotTouchTheScatter(unittest.TestCase):
    """The fault of 2026-09-08 was a requirement resting on a scatter that
    could not carry it. Now it may not reach the scatter at all, and this is
    proved by a RUN rather than by reading the code."""

    def test_the_requirement_stands_while_the_scatter_REFUSES(self):
        def refuse(*a, **k):
            raise SystemExit("the scatter is not measurable here")

        with mock.patch.object(req, "scatter_rows", refuse):
            with mock.patch.object(req, "scatter_range", refuse):
                self.assertAlmostEqual(req.published_lever(), 70.92, places=1)
                for flick in req.ASSUMED:
                    self.assertGreater(req.requirement(flick)["framesPerSecond"],
                                       0)

    def test_the_module_prints_the_requirement_even_with_no_keypoints(self):
        """`main` must still report, and say the scatter is missing, rather
        than failing. A machine without the recordings still plans a shoot."""
        def refuse(*a, **k):
            raise SystemExit("no keypoints on this machine")

        with mock.patch.object(req, "scatter_rows", refuse):
            with mock.patch("builtins.print") as printed:
                self.assertEqual(req.main([]), 0)

        said = " ".join(str(c.args[0]) for c in printed.call_args_list
                        if c.args)
        self.assertIn("PUBLISHED", said)
        self.assertIn("not measurable here", said)


class TheDocumentEqualsTheInstrument(unittest.TestCase):
    """Every published figure in the section, not only the table."""

    def table_rows(self) -> list[list[str]]:
        text = section_text()
        start = text.index("| the floor it must clear")
        block = text[start:text.index("\n\n", start)]
        return [[cell.strip() for cell in line.strip().strip("|").split("|")]
                for line in block.splitlines() if line.strip().startswith("|")]

    def header_flicks(self) -> list[req.Flick]:
        flicks = []
        for cell in self.table_rows()[0][1:]:
            found = re.fullmatch(r"(\d+) deg in (\d+) ms", cell)
            self.assertIsNotNone(found, f"unreadable column heading: {cell}")
            flicks.append(req.Flick(float(found[1]), float(found[2])))
        return flicks

    def test_the_columns_name_the_flicks_THE_MODULE_assumes(self):
        self.assertEqual(sorted(self.header_flicks()), sorted(req.ASSUMED))

    def test_every_cell_is_the_instrument_s_own_lever(self):
        """Rows are paired to the floor statistic they NAME in backticks, and
        columns to the flick in their heading. Never by order."""
        flicks = self.header_flicks()
        checked = 0
        for row in self.table_rows()[2:]:
            found = re.match(r"`(\w+)`, ([\d.]+) deg/s", row[0])
            self.assertIsNotNone(found, f"unreadable row label: {row[0]}")
            against, floor = found[1], float(found[2])
            self.assertIn(against, req.MEASURED_FLOOR._fields)
            self.assertAlmostEqual(getattr(req.MEASURED_FLOOR, against), floor,
                                   msg="the row quotes a floor the module "
                                       "does not carry")
            for flick, cell in zip(flicks, row[1:]):
                with self.subTest(against=against, flick=flick):
                    px = re.fullmatch(r"(\d+) px", cell)
                    self.assertIsNotNone(px, f"unreadable cell: {cell}")
                    self.assertEqual(int(px[1]),
                                     round(req.lever_for(flick, against)))
                    checked += 1

        self.assertEqual(checked, 6, "the table lost a row or a column")

    def test_the_prose_quotes_the_published_lever(self):
        self.assertIn(f"asks for {req.published_lever():.0f} px",
                      section_text())

    def test_the_document_quotes_the_two_frame_rates(self):
        text = section_text()
        for flick in req.ASSUMED:
            with self.subTest(flick=flick):
                self.assertIn(f"{req.frames_per_second_for(flick):.0f} fps",
                              text)

    def test_the_section_withdraws_BOTH_of_the_day_s_figures(self):
        """The 29-49 and the 88/73/41/69 are both gone, and the section says
        which and why. A withdrawal that does not name the number is not one."""
        text = section_text()

        self.assertIn("WITHDRAWN", text)
        self.assertIn("29 to 49 px", text)
        self.assertIn("88 / 73 / 41 / 69 px", text)
        self.assertIn("range", text.lower())

    def test_no_withdrawn_figure_is_still_quoted_as_a_REQUIREMENT(self):
        """The withdrawn numbers appear only in the sentence that withdraws
        them. If one climbs back into the table, this fails."""
        for row in self.table_rows()[2:]:
            for cell in row[1:]:
                with self.subTest(cell=cell):
                    self.assertNotIn(cell.strip(),
                                     ("88 px", "73 px", "41 px", "69 px",
                                      "29 px", "49 px"))

    def test_the_document_NAMES_the_instrument_that_made_its_numbers(self):
        text = findings_text()

        self.assertIn("spikes/video_flick_requirement.py", text)
        self.assertIn("spikes/test_video_flick_requirement.py", text)


class TheScatterIsReportedAsARangeAndSpentOnNothing(unittest.TestCase):

    def setUp(self):
        if not keypoints_present():
            self.skipTest("the keypoint artefacts are not on this machine")

    def test_the_two_windows_differ_in_stillness_which_is_the_point(self):
        """One window this pack PROVED still by its own search, one it called
        still by eye and which grows by more than a third. Reporting both is
        what makes the range honest."""
        rows = {r["window"].start: r for r in req.scatter_rows()}

        self.assertLess(rows[37]["forearmGrowth"], 0.10)
        self.assertGreater(rows[560]["forearmGrowth"], 0.30)

    def test_the_range_spans_both_windows_and_both_estimates(self):
        rows = req.scatter_rows()
        low, high = req.scatter_range(rows)
        every = [r[k] for r in rows for k in ("eFromAngle", "eFromStep")]

        self.assertAlmostEqual(low, min(every))
        self.assertAlmostEqual(high, max(every))
        self.assertGreater(high / low, 2.0,
                           "a range this narrow would not be a range")

    def scatter_table(self) -> dict[str, list[str]]:
        """The scatter table, keyed by the window each row NAMES."""
        text = section_text()
        start = text.index("| window of side 0.2 |")
        block = text[start:text.index("\n\n", start)]
        rows = {}
        for line in block.splitlines()[2:]:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            found = re.match(r"`(\d+)-(\d+)`", cells[0])
            self.assertIsNotNone(found, f"unreadable row label: {cells[0]}")
            rows[f"{found[1]}-{found[2]}"] = cells[1:]
        return rows

    def test_the_scatter_table_names_the_windows_THE_MODULE_measures(self):
        """Paired by the frames in the label, never by row order."""
        self.assertEqual(
            sorted(self.scatter_table()),
            sorted(f"{w.start}-{w.end}" for w in req.SCATTER_WINDOWS))

    def test_the_document_quotes_every_scatter_figure_it_publishes(self):
        table = self.scatter_table()
        checked = 0
        for row in req.scatter_rows():
            window = row["window"]
            with self.subTest(window=window.start):
                cells = table[f"{window.start}-{window.end}"]

                self.assertEqual(cells[0],
                                 f"{row['forearmGrowth'] * 100:.0f} per cent")
                self.assertEqual(cells[1], f"{row['angleSd']:.2f} deg")
                self.assertEqual(cells[2], f"{row['stepSd']:.2f} deg")
                self.assertEqual(cells[3], f"**{row['eFromAngle']:.2f} and "
                                           f"{row['eFromStep']:.2f} px**")
                checked += 1

        self.assertEqual(checked, len(req.SCATTER_WINDOWS))

    def test_the_document_quotes_the_range_itself(self):
        low, high = req.scatter_range()

        self.assertIn(f"**The range is {low:.2f} to {high:.2f} px.**",
                      section_text())

    def test_the_RANGE_relabelled_as_a_sigma_is_what_went_wrong(self):
        """The withdrawn `e = 3.0 px` is recovered by treating the 560-588
        window's RANGE as a one-sigma value. Proving the arithmetic of the
        mistake is what stops it being repeated."""
        row = [r for r in req.scatter_rows() if r["window"].start == 560][0]
        as_if = (row["angleRange"] * row["leverMean"]
                 / (req.DEGREES_PER_RADIAN * 2 ** 0.5))

        self.assertAlmostEqual(as_if, 2.9, places=0)
        self.assertGreater(as_if / row["eFromStep"], 4.0)


class OneRequirementHasOneHome(unittest.TestCase):

    def test_the_filming_guide_carries_NO_pixel_figure_of_its_own(self):
        """A number in two documents is a number that will disagree with
        itself, which is exactly what happened on 2026-09-08."""
        text = FILMING_GUIDE.read_text(encoding="utf-8")
        start = text.index("## If the wrists and fingers matter")
        section = text[start:text.index("\n## ", start + 4)]

        self.assertEqual(re.findall(r"\d+\s*(?:px|pixels)", section), [])
        self.assertIn("VIDEO_CAPTURE_FINDINGS.md", section)

    def test_the_findings_document_is_the_home_and_says_so(self):
        self.assertIn("put enough pixels on the hands to measure a wrist",
                      findings_text())


if __name__ == "__main__":
    unittest.main()
