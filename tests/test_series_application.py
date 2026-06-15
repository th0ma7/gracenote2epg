"""Regression test: series details must enrich EVERY airing, not just the first.

A single series airs many times across the guide (e.g. a daily soap). The
extended details (box-art image, credits, genres, synopsis) must be applied to
each airing; an earlier version stopped after the first airing of each series,
leaving later airings with only the per-episode thumbnail as <icon>.
"""

import tempfile
import unittest
from pathlib import Path

from gracenote2epg.cache import CacheManager
from gracenote2epg.parser.base import DataParser


SERIES_DETAILS = {
    "seriesImage": "p183907_b_h9_at",  # box art (_b_)
    "backgroundImage": "p183907_i_h10_ag",
    "seriesGenres": "Drama|Romance",
    "seriesDescription": "Generic series blurb.",
    "overviewTab": {"cast": [{"role": "Actor", "name": "Jane Star"}], "crew": []},
    "upcomingEpisodeTab": [],
}


class ApplyToEveryAiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dp = DataParser(CacheManager(Path(self.tmp) / "cache"))

        self.reads = []  # series_ids read from disk

        def fake_get(series_id):
            self.reads.append(series_id)
            return SERIES_DETAILS if series_id == "EP00041092" else None

        self.dp.series_downloader.get_cached_series_details = fake_get

    def _airing(self, epid):
        return {"epseries": "EP00041092", "epid": epid, "epimage": None, "epfan": None}

    def test_all_airings_of_a_series_are_enriched(self):
        self.dp.schedule = {
            "72755": {
                "ch72755": {"name": "channel meta"},  # must be skipped
                "ep1": self._airing("EP000410923395"),
                "ep2": self._airing("EP000410923396"),
                "ep3": self._airing("EP000410923397"),
            }
        }

        self.dp._apply_series_details_to_schedule()

        sched = self.dp.schedule["72755"]
        for key in ("ep1", "ep2", "ep3"):
            self.assertEqual(
                sched[key]["epimage"],
                "p183907_b_h9_at",
                f"{key} should get the series box-art image",
            )
            self.assertEqual(sched[key]["epfan"], "p183907_i_h10_ag")
            self.assertIn("epcredits", sched[key], f"{key} should get credits")

    def test_disk_is_read_once_per_series(self):
        self.dp.schedule = {
            "72755": {
                "ep1": self._airing("EP000410923395"),
                "ep2": self._airing("EP000410923396"),
            }
        }
        self.dp._apply_series_details_to_schedule()
        # Cached per series: one disk read even though there are two airings.
        self.assertEqual(self.reads, ["EP00041092"])

    def test_series_without_details_left_untouched(self):
        ep = {"epseries": "SH99999999", "epid": "x", "epimage": None}
        self.dp.schedule = {"72755": {"ep1": ep}}
        self.dp._apply_series_details_to_schedule()
        self.assertIsNone(ep["epimage"])


if __name__ == "__main__":
    unittest.main()
