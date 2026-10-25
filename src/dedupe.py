"""Notification deduplication store."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any, Dict, Iterable, List

logger = logging.getLogger(__name__)


def slot_fingerprint(slot: Dict[str, Any]) -> str:
    key = "|".join(
        [
            str(slot.get("visa_location", "")),
            str(slot.get("visa_type", slot.get("category", ""))),
            str(slot.get("start_date", "")),
            str(slot.get("slots", "")),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


class DedupeStore:
    """Skip re-alerting on the same slot fingerprint within a TTL window."""

    def __init__(self, path: str, ttl_hours: int = 6):
        self.path = path
        self.ttl_seconds = ttl_hours * 3600
        self._entries: Dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            now = time.time()
            self._entries = {
                k: float(v)
                for k, v in data.items()
                if now - float(v) < self.ttl_seconds
            }
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
            self._entries = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(self._entries, fh)

    def filter_new(self, slots: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        now = time.time()
        # Drop expired
        self._entries = {
            k: v for k, v in self._entries.items() if now - v < self.ttl_seconds
        }
        fresh: List[Dict[str, Any]] = []
        for slot in slots:
            fp = slot_fingerprint(slot)
            if fp in self._entries:
                logger.info("Skipping duplicate slot alert: %s", fp)
                continue
            fresh.append(slot)
        return fresh

    def mark_alerted(self, slots: Iterable[Dict[str, Any]]) -> None:
        now = time.time()
        for slot in slots:
            self._entries[slot_fingerprint(slot)] = now
        self._save()
