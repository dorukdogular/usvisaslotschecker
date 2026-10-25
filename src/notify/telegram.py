"""Telegram Bot API notifications."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..client import CFSafeClient
from ..config import Config
from .formatters import build_message, build_title

logger = logging.getLogger(__name__)


def send_telegram_notification(
    slots: List[Dict[str, Any]], config: Config
) -> bool:
    if not config.has_telegram:
        logger.warning("Telegram configuration missing")
        return False

    title = build_title(slots)
    body = build_message(slots)
    text = f"<b>{title}</b>\n\n{body}"

    url = (
        f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    )
    payload = {
        "chat_id": config.telegram_chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    try:
        # Use a plain session without chrome-extension headers for Telegram
        client = CFSafeClient(config)
        response = client.session.post(
            url,
            data=payload,
            proxies=config.proxies,
            timeout=config.request_timeout,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                logger.info("Telegram notification sent successfully")
                return True
            logger.error("Telegram API error: %s", data)
            return False
        logger.error(
            "Telegram failed status=%s body=%s",
            response.status_code,
            response.text[:300],
        )
        return False
    except Exception as exc:
        logger.exception("Error sending Telegram notification: %s", exc)
        return False
