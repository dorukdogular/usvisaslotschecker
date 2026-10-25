"""SMTP email notifications."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List

from ..config import Config
from .formatters import build_message, build_title

logger = logging.getLogger(__name__)


def send_email(slots: List[Dict[str, Any]], config: Config) -> bool:
    if not config.has_email:
        logger.warning(
            "Email configuration missing. Set SENDER_EMAIL, "
            "SENDER_PASSWORD, and RECEIVER_EMAIL."
        )
        return False

    msg = MIMEMultipart()
    msg["From"] = config.sender_email
    msg["To"] = config.receiver_email
    msg["Subject"] = build_title(slots)
    msg.attach(MIMEText(build_message(slots), "plain", "utf-8"))

    try:
        logger.info(
            "Connecting to SMTP server %s:%s",
            config.smtp_host,
            config.smtp_port,
        )
        server = smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30)
        if config.smtp_use_tls:
            server.starttls()
        server.login(config.sender_email, config.sender_password)
        server.send_message(msg)
        server.quit()
        logger.info("Email notification sent successfully")
        return True
    except Exception as exc:
        logger.exception("Failed to send email: %s", exc)
        return False
