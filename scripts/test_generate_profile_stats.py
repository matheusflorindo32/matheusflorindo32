"""Regression tests for transient GitHub API failures in profile statistics."""
import json
import unittest
import urllib.error
from http.client import RemoteDisconnected
from unittest.mock import patch

import generate_profile_stats as stats


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"ok": true}'


class GitHubApiRetryTests(unittest.TestCase):
    @patch.object(stats.time, "sleep")
    @patch.object(stats.urllib.request, "urlopen")
    def test_retries_remote_disconnection_then_succeeds(self, urlopen, sleep):
        urlopen.side_effect = [RemoteDisconnected("remote closed"), FakeResponse()]
        self.assertEqual(stats.api_get("/users/test"), {"ok": True})
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch.object(stats.time, "sleep")
    @patch.object(stats.urllib.request, "urlopen")
    def test_does_not_retry_authentication_error(self, urlopen, sleep):
        urlopen.side_effect = urllib.error.HTTPError("https://api.github.com", 401, "unauthorized", {}, None)
        with self.assertRaises(urllib.error.HTTPError):
            stats.api_get("/users/test")
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    @patch.object(stats.time, "sleep")
    @patch.object(stats.urllib.request, "urlopen")
    def test_retries_transient_503(self, urlopen, sleep):
        urlopen.side_effect = [
            urllib.error.HTTPError("https://api.github.com", 503, "temporarily unavailable", {}, None),
            FakeResponse(),
        ]
        self.assertEqual(stats.api_get("/users/test"), {"ok": True})
        self.assertEqual(urlopen.call_count, 2)

    @patch.object(stats.time, "sleep")
    @patch.object(stats.urllib.request, "urlopen")
    def test_exhaustion_raises_instead_of_hiding_failure(self, urlopen, sleep):
        urlopen.side_effect = [RemoteDisconnected("closed") for _ in range(3)]
        with self.assertRaises(RemoteDisconnected):
            stats.api_get("/users/test")
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleep.call_count, 2)


if __name__ == "__main__":
    unittest.main()
