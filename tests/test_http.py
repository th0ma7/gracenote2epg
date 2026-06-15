"""Tests for the Gracenote HTTP adapter (execute), using a fake session."""

import unittest

from gracenote2epg.downloader.http import execute
from gracenote2epg.downloader.tasks import DownloadTask


class FakeResponse:
    def __init__(self, status_code=200, text="{}", content=b"{}"):
        self.status_code = status_code
        self.text = text
        self.content = content


class FakeSession:
    def __init__(self, response=None, raises=None):
        self._response = response or FakeResponse()
        self._raises = raises
        self.posted = None
        self.got = None

    def post(self, url, **kw):
        self.posted = (url, kw)
        if self._raises:
            raise self._raises
        return self._response

    def get(self, url, **kw):
        self.got = (url, kw)
        if self._raises:
            raise self._raises
        return self._response


def series_task():
    return DownloadTask(
        "SH1",
        "https://h/api/program/overviewDetails",
        "series_details",
        data=b"programSeriesID=SH1",
    )


def guide_task():
    return DownloadTask("2026010100", "https://h/api/grid?x=1", "guide_block")


class ExecuteTests(unittest.TestCase):
    def test_series_uses_post_with_body(self):
        s = FakeSession(FakeResponse(200, '{"ok":1}', b'{"ok":1}'))
        r = execute(s, series_task())
        self.assertTrue(r.success)
        self.assertEqual(r.content, b'{"ok":1}')
        self.assertEqual(s.posted[0], "https://h/api/program/overviewDetails")
        self.assertIsNone(s.got)  # not a GET

    def test_guide_uses_get(self):
        s = FakeSession(FakeResponse(200, "{}", b"{}"))
        r = execute(s, guide_task())
        self.assertTrue(r.success)
        self.assertIsNotNone(s.got)
        self.assertIsNone(s.posted)

    def test_429_is_rate_limited(self):
        r = execute(FakeSession(FakeResponse(429, "Too Many Requests")), series_task())
        self.assertFalse(r.success)
        self.assertTrue(r.rate_limited)
        self.assertEqual(r.http_code, 429)

    def test_waf_challenge_body_is_rate_limited(self):
        body = "<html>... AwsWafIntegration challenge.js ...</html>"
        r = execute(FakeSession(FakeResponse(200, body, body.encode())), series_task())
        self.assertFalse(r.success)
        self.assertTrue(r.rate_limited)

    def test_exception_is_a_failure_not_a_crash(self):
        r = execute(FakeSession(raises=OSError("connection reset")), series_task())
        self.assertFalse(r.success)
        self.assertFalse(r.rate_limited)
        self.assertIn("connection reset", r.error)


if __name__ == "__main__":
    unittest.main()
