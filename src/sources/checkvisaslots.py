"""checkvisaslots.com API source (Phase 1 primary)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..client import CFSafeClient, CloudflareBlockedError
from ..config import Config

logger = logging.getLogger(__name__)

# Headers mimic the checkvisaslots Chrome extension (required by their API).
CHECKVISASLOTS_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8,tr;q=0.7",
    "extversion": "4.6.1",
    "origin": "chrome-extension://beepaenfejnphdgnkmccjcfiieihhogl",
    "priority": "u=1, i",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "Windows",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "cross-site",
}


def fetch_checkvisaslots(
    config: Config, client: CFSafeClient
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not config.api_key:
        raise RuntimeError("API_KEY is required for checkvisaslots source")

    headers = dict(CHECKVISASLOTS_HEADERS)
    headers["x-api-key"] = config.api_key
    result = client.get(config.checkvisaslots_url, headers=headers)

    if result.status_code >= 400:
        if result.status_code in {403, 429, 503}:
            raise CloudflareBlockedError(result.status_code, result.text)
        raise RuntimeError(
            f"checkvisaslots HTTP {result.status_code}: {result.text[:300]}"
        )

    data = result.json_data
    if not isinstance(data, dict):
        raise RuntimeError(
            f"Unexpected checkvisaslots response type: {type(data)}"
        )

    slots = data.get("slotDetails") or []
    if not isinstance(slots, list):
        slots = []

    logger.info(
        "Fetched %s slot rows from checkvisaslots (via_solver=%s)",
        len(slots),
        result.via_solver,
    )
    return slots, data
