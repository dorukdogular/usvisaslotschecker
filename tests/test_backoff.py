"""Backoff controller tests."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.client import BackoffController  # noqa: E402


class BackoffTests(unittest.TestCase):
    def test_exponential_backoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "backoff.json")
            ctrl = BackoffController(path, max_minutes=60)
            self.assertEqual(ctrl.should_wait(), 0)
            self.assertEqual(ctrl.record_failure(), 15)
            self.assertGreater(ctrl.should_wait(), 0)
            self.assertEqual(ctrl.record_failure(), 30)
            self.assertEqual(ctrl.record_failure(), 60)
            self.assertEqual(ctrl.record_failure(), 60)  # capped
            ctrl.record_success()
            self.assertEqual(ctrl.should_wait(), 0)


if __name__ == "__main__":
    unittest.main()
