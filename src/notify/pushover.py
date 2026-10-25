"""Optional Pushover notifications (kept for back-compat)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..config import Config
from .formatters import build_message, build_title

logger = logging.getLogger(__name__)


def send_pushover_notification(
    slots: List[Dict[str, Any]], config: Config
) -> bool:
    if not config.has_pushover:
        logger.warning("Pushover configuration missing")
        return False

    try:
        from curl_cffi import requests as cffi_requests

        payload = {
            "token": config.pushover_token,
            "user": config.pushover_user,
            "message": build_message(slots),
            "title": build_title(slots),
            "priority": 1,
        }
        response = cffi_requests.post(
            "https://api.pushover.net/1/messages.json",
            data=payload,
            proxies=config.proxies,
            timeout=config.request_timeout,
            impersonate=config.impersonate,
        )
        if response.status_code == 200:
            logger.info("Pushover notification sent successfully")
            return True
        logger.error(
            "Pushover failed status=%s body=%s",
            response.status_code,
            response.text[:300],
        )
        return False
    except Exception as exc:
        logger.exception("Error sending Pushover notification: %s", exc)
        return False
