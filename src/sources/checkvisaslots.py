"""checkvisaslots.com API source (Phase 1 primary)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..client import CFSafeClient, CloudflareBlockedError
from ..config import Config

logger = logging.getLogger(__name__)


def fetch_checkvisaslots(
    config: Config, client: CFSafeClient
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if not config.api_key:
        raise RuntimeError("API_KEY is required for checkvisaslots source")

    headers = {"x-api-key": config.api_key}
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
