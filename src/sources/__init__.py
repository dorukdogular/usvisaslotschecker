"""Slot data sources."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..client import CFSafeClient
from ..config import Config
from .checkvisaslots import fetch_checkvisaslots
from .official import fetch_official


def fetch_slots(
    config: Config, client: CFSafeClient
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Return (slot_details, raw_payload)."""
    if config.source == "official":
        return fetch_official(config, client)
    return fetch_checkvisaslots(config, client)
