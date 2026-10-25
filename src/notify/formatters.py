"""Shared message formatting for notifications (Europe/Istanbul)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo


ISTANBUL = ZoneInfo("Europe/Istanbul")


def parse_createdon(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    # Common format from checkvisaslots: "Mon, 01 Jan 2026 12:00:00 GMT"
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    # Fallback: treat as UTC naive
    try:
        from dateutil import parser as date_parser

        dt = date_parser.parse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def format_istanbul(value: Optional[str]) -> str:
    dt = parse_createdon(value)
    if dt is None:
        return value or "N/A"
    return dt.astimezone(ISTANBUL).strftime("%Y-%m-%d %H:%M:%S %Z")


def build_message(slots: List[Dict[str, Any]]) -> str:
    lines = ["İstanbul ABD Konsolosluğu — müsait randevu bulundu!", ""]
    for slot in slots:
        category = (
            slot.get("visa_type")
            or slot.get("visa_category")
            or slot.get("category")
            or "N/A"
        )
        lines.append(f"Lokasyon: {slot.get('visa_location', 'N/A')}")
        lines.append(f"Kategori: {category}")
        lines.append(f"Slot sayısı: {slot.get('slots', 'N/A')}")
        lines.append(f"Başlangıç: {slot.get('start_date', 'N/A')}")
        lines.append(f"Güncelleme: {format_istanbul(slot.get('createdon'))}")
        lines.append("")
    lines.append("Hemen kontrol et: https://www.ustraveldocs.com/tr")
    return "\n".join(lines)


def build_title(slots: List[Dict[str, Any]]) -> str:
    locs = sorted(
        {
            str(s.get("visa_location", "ISTANBUL"))
            for s in slots
            if s.get("visa_location")
        }
    )
    loc = locs[0] if len(locs) == 1 else "ABD Vize"
    return f"{loc} — randevu slotu bulundu"
