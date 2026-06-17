#!/usr/bin/env python3
"""
build-geodata.py - regenerate the bundled postal-code geo dataset.

Downloads the GeoNames postal-code data for Canada and the USA and writes a
compact, trimmed, gzipped CSV bundled in the package
(gracenote2epg/data/geopostal.csv.gz). This replaces the pgeocode/pandas/numpy
dependency with a stdlib-only lookup.

This is a MAINTENANCE tool, run by hand before a release (not during the wheel
build) so packaging stays offline and reproducible:

    python3 scripts/build-geodata.py
    git add gracenote2epg/data/geopostal.csv.gz && git commit

GeoNames postal data is licensed CC BY 4.0 (https://www.geonames.org/).
"""

import csv
import gzip
import io
import sys
import urllib.request
import zipfile
from pathlib import Path

# GeoNames postal export: tab-separated, columns documented at
# https://download.geonames.org/export/zip/readme.txt
#   0 country  1 postal  2 place_name  3 admin1_name  4 admin1_code
#   5 admin2_name  6 admin2_code  7 admin3_name  8 admin3_code
#   9 lat  10 lon  11 accuracy
COUNTRIES = ["CA", "US"]
BASE_URL = "https://download.geonames.org/export/zip/{}.zip"

OUT = Path(__file__).resolve().parent.parent / "gracenote2epg" / "data" / "geopostal.csv.gz"

# Output columns (names match the fields the geocoder reads, mirroring pgeocode)
HEADER = [
    "country",
    "postal",
    "place_name",
    "state_code",
    "state_name",
    "county_name",
    "community_name",
]


def fetch_country(country: str):
    url = BASE_URL.format(country)
    print(f"  downloading {url} ...", flush=True)
    blob = urllib.request.urlopen(url, timeout=60).read()
    zf = zipfile.ZipFile(io.BytesIO(blob))
    text = zf.read(f"{country}.txt").decode("utf-8")
    seen = set()
    rows = []
    for rec in csv.reader(io.StringIO(text), delimiter="\t"):
        if len(rec) < 5:
            continue
        country_code, postal, place = rec[0], rec[1], rec[2]
        admin1_name, admin1_code = rec[3], rec[4]
        admin2_name = rec[5] if len(rec) > 5 else ""
        admin3_name = rec[7] if len(rec) > 7 else ""
        key = (country_code, postal)
        if key in seen:  # keep first occurrence per (country, postal)
            continue
        seen.add(key)
        rows.append(
            [country_code, postal, place, admin1_code, admin1_name, admin2_name, admin3_name]
        )
    print(f"  {country}: {len(rows)} unique postal codes")
    return rows


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    all_rows = []
    for c in COUNTRIES:
        all_rows.extend(fetch_country(c))

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(HEADER)
    w.writerows(all_rows)
    data = buf.getvalue().encode("utf-8")

    # mtime=0 for reproducible, stable gzip output across regenerations
    with gzip.GzipFile(filename="", mode="wb", fileobj=open(OUT, "wb"), mtime=0) as gz:
        gz.write(data)

    size = OUT.stat().st_size
    print(f"wrote {OUT} ({len(all_rows)} rows, {size // 1024} KiB gzip)")


if __name__ == "__main__":
    sys.exit(main())
