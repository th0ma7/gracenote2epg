"""Tests for SeriesParser: crew capture, TV credits, per-episode synopsis."""

import unittest

from gracenote2epg.parser.series import SeriesParser


def _details(**over):
    base = {
        "seriesDescription": "Generic series blurb.",
        "seriesImage": "p1_v_h9_aa",
        "backgroundImage": "p1_k_h9_aa",
        "seriesGenres": "Comedy",
        "overviewTab": {
            "cast": [{"role": "Actor", "name": "Jane Star", "characterName": "Lead"}],
            "crew": [
                {"role": "Director", "name": "Sam Helm"},
                {"role": "Writer", "name": "Pat Pen"},
            ],
        },
        "upcomingEpisodeTab": [],
    }
    base.update(over)
    return base


class CreditsTests(unittest.TestCase):
    def setUp(self):
        self.p = SeriesParser()

    def test_tv_series_get_credits(self):
        ep = {"epid": "EP000000010001"}
        self.p.parse_series_details(ep, _details(), "EP00000001")
        self.assertIn("epcredits", ep, "TV series should now receive credits")

    def test_cast_and_crew_merged(self):
        ep = {"epid": "EP000000010001"}
        self.p.parse_series_details(ep, _details(), "EP00000001")
        names = [c["name"] for c in ep["epcredits"]]
        self.assertEqual(names, ["Jane Star", "Sam Helm", "Pat Pen"])
        roles = {c["role"] for c in ep["epcredits"]}
        self.assertEqual(roles, {"Actor", "Director", "Writer"})

    def test_missing_crew_is_fine(self):
        d = _details()
        d["overviewTab"]["crew"] = []
        ep = {"epid": "x"}
        self.p.parse_series_details(ep, d, "MV00000001")
        self.assertEqual([c["name"] for c in ep["epcredits"]], ["Jane Star"])


class SynopsisTests(unittest.TestCase):
    def setUp(self):
        self.p = SeriesParser()

    def test_episode_synopsis_overrides_series_description(self):
        d = _details(
            upcomingEpisodeTab=[
                {"tmsID": "EP000000010001", "synopsis": "This specific episode does X."}
            ]
        )
        ep = {"epid": "EP000000010001"}
        self.p.parse_series_details(ep, d, "EP00000001")
        self.assertEqual(ep["epseriesdesc"], "This specific episode does X.")

    def test_no_synopsis_keeps_series_description(self):
        ep = {"epid": "EP000000010001"}
        self.p.parse_series_details(ep, _details(), "EP00000001")
        self.assertEqual(ep["epseriesdesc"], "Generic series blurb.")


class DisplayRatingTests(unittest.TestCase):
    def setUp(self):
        self.p = SeriesParser()

    def test_display_rating_fills_missing_guide_rating(self):
        d = _details(upcomingEpisodeTab=[{"tmsID": "EP000000010001", "displayRating": "TV-14"}])
        ep = {"epid": "EP000000010001"}  # no eprating from the guide
        self.p.parse_series_details(ep, d, "EP00000001")
        self.assertEqual(ep["eprating"], "TV-14")

    def test_guide_rating_takes_precedence(self):
        d = _details(upcomingEpisodeTab=[{"tmsID": "EP000000010001", "displayRating": "TV-14"}])
        ep = {"epid": "EP000000010001", "eprating": "PG"}  # guide already set it
        self.p.parse_series_details(ep, d, "EP00000001")
        self.assertEqual(ep["eprating"], "PG")


class ImagesTests(unittest.TestCase):
    def test_background_image_parsed_to_epfan(self):
        ep = {"epid": "x"}
        SeriesParser().parse_series_details(ep, _details(), "EP00000001")
        self.assertEqual(ep["epfan"], "p1_k_h9_aa")
        self.assertEqual(ep["epimage"], "p1_v_h9_aa")


if __name__ == "__main__":
    unittest.main()
