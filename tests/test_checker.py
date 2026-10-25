"""Unit tests for slot filtering and dedupe."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.checker import filter_slots, is_within_duration  # noqa: E402
from src.config import Config  # noqa: E402
from src.dedupe import DedupeStore, slot_fingerprint  # noqa: E402


def _future(days: int = 30) -> str:
    return (datetime.now().date() + timedelta(days=days)).strftime("%d %b %Y")


class CheckerTests(unittest.TestCase):
    def test_within_duration_rejects_past(self):
        past = (datetime.now().date() - timedelta(days=2)).strftime("%d %b %Y")
        self.assertFalse(is_within_duration(past, 120))

    def test_istanbul_match_without_vac_and(self):
        config = Config(
            visa_locations=["ISTANBUL"],
            visa_categories=["B1/B2"],
            require_both_consulate_and_vac=False,
            visa_duration_days=120,
        )
        slots = [
            {
                "visa_location": "ISTANBUL",
                "visa_type": "B1/B2",
                "slots": 3,
                "start_date": _future(20),
                "createdon": "Mon, 01 Jan 2026 12:00:00 GMT",
            },
            {
                "visa_location": "ANKARA",
                "visa_type": "B1/B2",
                "slots": 5,
                "start_date": _future(10),
            },
            {
                "visa_location": "ISTANBUL",
                "visa_type": "C1/D",
                "slots": 2,
                "start_date": _future(15),
            },
        ]
        matched = filter_slots(slots, config)
        self.assertEqual(len(matched), 1)
        self.assertEqual(matched[0]["visa_location"], "ISTANBUL")
        self.assertEqual(matched[0]["visa_type"], "B1/B2")

    def test_legacy_and_mode(self):
        config = Config(
            visa_locations=["NEW DELHI", "NEW DELHI VAC"],
            visa_categories=[],
            require_both_consulate_and_vac=True,
            visa_duration_days=120,
        )
        slots = [
            {
                "visa_location": "NEW DELHI",
                "slots": 1,
                "start_date": _future(5),
            },
            {
                "visa_location": "NEW DELHI VAC",
                "slots": 2,
                "start_date": _future(6),
            },
        ]
        matched = filter_slots(slots, config)
        self.assertEqual(len(matched), 2)

        # Only consulate → no alert
        matched2 = filter_slots(slots[:1], config)
        self.assertEqual(matched2, [])


class DedupeTests(unittest.TestCase):
    def test_dedupe_filters_repeats(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "last_alert.json")
            store = DedupeStore(path, ttl_hours=6)
            slot = {
                "visa_location": "ISTANBUL",
                "visa_type": "B1/B2",
                "start_date": "17 Feb 2026",
                "slots": 2,
            }
            fresh = store.filter_new([slot])
            self.assertEqual(len(fresh), 1)
            store.mark_alerted(fresh)

            store2 = DedupeStore(path, ttl_hours=6)
            again = store2.filter_new([slot])
            self.assertEqual(again, [])
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertIn(slot_fingerprint(slot), data)


if __name__ == "__main__":
    unittest.main()
