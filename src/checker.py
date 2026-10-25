"""Slot filtering logic for Istanbul (and optional India AND-mode)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from dateutil import parser as date_parser

from .config import Config

logger = logging.getLogger(__name__)

# Common alternate keys that checkvisaslots / community feeds may use
CATEGORY_KEYS = (
    "visa_type",
    "visa_category",
    "category",
    "visa_class",
    "class",
)


def parse_slot_date(date_str: str) -> Optional[datetime.date]:
    try:
        return date_parser.parse(date_str).date()
    except (ValueError, TypeError, OverflowError) as exc:
        logger.warning("Could not parse date %r: %s", date_str, exc)
        return None


def is_within_duration(date_str: str, duration_days: int, today=None) -> bool:
    start_date = parse_slot_date(date_str)
    if start_date is None:
        return False
    if today is None:
        today = datetime.now().date()
    end_date = today + timedelta(days=duration_days)
    return today <= start_date <= end_date


def slot_category(slot: Dict[str, Any]) -> Optional[str]:
    for key in CATEGORY_KEYS:
        value = slot.get(key)
        if value:
            return str(value).strip()
    return None


def category_matches(slot: Dict[str, Any], allowed: List[str]) -> bool:
    if not allowed:
        return True
    cat = slot_category(slot)
    if cat is None:
        # API may not expose category on every row — keep location match
        return True
    allowed_norm = {a.strip().upper() for a in allowed}
    return cat.upper() in allowed_norm or any(
        a in cat.upper() for a in allowed_norm
    )


def filter_slots(
    slot_details: List[Dict[str, Any]], config: Config
) -> List[Dict[str, Any]]:
    """Return slots that match configured locations/categories/window."""
    locations = {loc.upper() for loc in config.visa_locations}
    consulate_slots: List[Dict[str, Any]] = []
    vac_slots: List[Dict[str, Any]] = []
    matched: List[Dict[str, Any]] = []

    for slot in slot_details:
        try:
            slots_count = int(slot.get("slots") or 0)
        except (TypeError, ValueError):
            slots_count = 0
        if slots_count <= 0:
            continue
        if "start_date" not in slot or not slot["start_date"]:
            continue
        if not is_within_duration(slot["start_date"], config.visa_duration_days):
            continue
        if not category_matches(slot, config.visa_categories):
            continue

        location = str(slot.get("visa_location", "")).strip()
        location_upper = location.upper()

        if config.require_both_consulate_and_vac:
            # Legacy India mode: split VAC vs consulate by name heuristic
            if "VAC" in location_upper:
                if location_upper in locations or any(
                    loc in location_upper for loc in locations
                ):
                    vac_slots.append(slot)
            elif location_upper in locations:
                consulate_slots.append(slot)
            continue

        if location_upper in locations:
            matched.append(slot)

    if config.require_both_consulate_and_vac:
        if consulate_slots and vac_slots:
            return consulate_slots + vac_slots
        return []

    return matched


def summarize_activity(data: Dict[str, Any]) -> Tuple[Optional[int], str]:
    activity = data.get("userActivity") or {}
    remaining = activity.get("remaining")
    try:
        remaining_int = int(remaining) if remaining is not None else None
    except (TypeError, ValueError):
        remaining_int = None
    msg = f"Remaining API calls: {remaining if remaining is not None else 'N/A'}"
    return remaining_int, msg
