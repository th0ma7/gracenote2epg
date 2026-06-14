"""Golden-file regression test for XMLTV generation.

Feeds a fixed parsed schedule through XmltvGenerator and compares the output
to a committed golden file. The timezone is pinned to UTC so the generated
times (and the +0000 offset) are reproducible on any host.

Regenerate the golden after an *intended* format change with:
    python3 -m tests.test_xmltv_golden --update-golden
"""

import os
import sys
import time
import tempfile
import unittest
from pathlib import Path

GOLDEN = Path(__file__).parent / "fixtures" / "xmltv_golden.xml"


def build_schedule():
    """A small but representative schedule: one station, a movie and a show."""
    return {
        "12345": {
            "chnum": "3.1",
            "chfcc": "WXYZ",
            "chnam": "Example TV",
            "chtvh": "Example TV HD",
            "chicon": "//example.com/logo.png",
            # Movie entry
            "MV00000001": {
                "epstart": "1800000000",
                "epend": "1800007200",
                "epshow": "The Example Movie",
                "epdesc": "A film about testing.",
                "epseriesdesc": "A film about testing, extended.",
                "epid": "MV000000010000",
                "epyear": "1959",
                "eprating": "PG",
                "epstar": "3",
                "eplength": "120",
                "epthumb": "p0000001_v_v1",
                "epfilter": ["Movie"],
                "epgenres": ["Movie", "Drama"],
                "epflag": ["Premiere"],
                "eptags": ["CC", "Stereo"],
                "epcredits": [
                    {"role": "director", "name": "Jane Director"},
                    {"role": "actor", "name": "John Lead", "characterName": "Hero"},
                    {"role": "voice", "name": "Sam Voice"},
                ],
            },
            # TV episode entry
            "EP00000002": {
                "epstart": "1800007200",
                "epend": "1800009000",
                "epshow": "Example Series",
                "eptitle": "The Pilot",
                "epdesc": "First episode.",
                "epseriesdesc": "First episode, extended description.",
                "epid": "EP000000020001",
                "epsn": "1",
                "epen": "1",
                "eplength": "30",
                "epimage": "p0000002_b_v1",
                "epfilter": ["Sitcom"],
                "epgenres": ["Comedy", "Sitcom"],
                "epflag": ["New"],
                "eptags": ["CC", "HD"],
            },
        }
    }


def build_config():
    return {
        "xdetails": True,
        "xdesc": True,
        "langdetect": False,
        "stitle": False,
        "epgenre": "3",
        "epicon": "1",
        "zipcode": "J3B1M4",
    }


def generate(path: Path):
    """Generate XMLTV for the fixed schedule at *path* (UTC-pinned)."""
    from gracenote2epg.cache import CacheManager
    from gracenote2epg.xmltv import XmltvGenerator

    os.environ["TZ"] = "UTC"
    time.tzset()
    cache_dir = path.parent / "_cache"
    cm = CacheManager(cache_dir)
    gen = XmltvGenerator(cm)
    gen.generate_xmltv(build_schedule(), build_config(), path)


class XmltvGoldenTests(unittest.TestCase):
    def test_output_matches_golden(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "xmltv.xml"
            generate(out)
            produced = out.read_text(encoding="utf-8")
        self.assertTrue(
            GOLDEN.exists(),
            "golden file missing; run: python3 -m tests.test_xmltv_golden --update-golden",
        )
        expected = GOLDEN.read_text(encoding="utf-8")
        self.assertEqual(
            produced, expected, "XMLTV output drifted from the golden file"
        )


def _update_golden():
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "xmltv.xml"
        generate(out)
        GOLDEN.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"golden updated: {GOLDEN}")


if __name__ == "__main__":
    if "--update-golden" in sys.argv:
        _update_golden()
    else:
        unittest.main()
