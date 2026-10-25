"""Notification channels."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from ..config import Config
from .email_notify import send_email
from .pushover import send_pushover_notification
from .telegram import send_telegram_notification

logger = logging.getLogger(__name__)


def notify_all(slots: List[Dict[str, Any]], config: Config) -> None:
    if not slots:
        return
    if config.dry_run or not config.notify:
        logger.info("NOTIFY disabled / dry-run — skipping outbound alerts")
        return

    if config.has_telegram:
        send_telegram_notification(slots, config)
    else:
        logger.info("Telegram not configured — skipping")

    if config.has_email:
        send_email(slots, config)
    else:
        logger.info("Email not configured — skipping")

    if config.has_pushover:
        send_pushover_notification(slots, config)
