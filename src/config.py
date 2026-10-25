"""Environment-based configuration with Istanbul defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Optional


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_list(name: str, default: str) -> List[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _default_data_dir() -> str:
    """Prefer /app/data inside the container; fall back to ./data locally."""
    if os.path.isdir("/app"):
        return "/app/data"
    return os.path.join(os.getcwd(), "data")


@dataclass
class Config:
    """Runtime configuration loaded from environment variables."""

    api_key: Optional[str] = None
    source: str = "checkvisaslots"
    visa_locations: List[str] = field(default_factory=lambda: ["ISTANBUL"])
    visa_categories: List[str] = field(default_factory=lambda: ["B1/B2"])
    visa_duration_days: int = 120
    require_both_consulate_and_vac: bool = False
    check_interval_minutes: int = 5
    check_jitter_seconds: int = 90
    notify: bool = True
    dry_run: bool = False

    # Notifications
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    sender_email: Optional[str] = None
    sender_password: Optional[str] = None
    receiver_email: Optional[str] = None
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_use_tls: bool = True
    pushover_token: Optional[str] = None
    pushover_user: Optional[str] = None

    # Networking
    proxy_url: Optional[str] = None
    cf_solver_url: Optional[str] = None
    request_timeout: int = 30
    impersonate: str = "chrome"

    # Paths / dedupe
    data_dir: str = "data"
    dedupe_hours: int = 6
    health_file: str = "data/last_success.txt"
    backoff_file: str = "data/backoff.json"

    # Official source (Phase 2, optional)
    official_email: Optional[str] = None
    official_password: Optional[str] = None
    official_base_url: str = "https://www.ustraveldocs.com/tr"

    # API
    checkvisaslots_url: str = "https://app.checkvisaslots.com/slots/v3"
    timezone: str = "Asia/Istanbul"

    @classmethod
    def from_env(cls) -> "Config":
        proxy_url = os.environ.get("PROXY_URL") or None
        if not proxy_url:
            # Back-compat with old PROXY_IP / PROXY_PORT
            proxy_ip = os.environ.get("PROXY_IP")
            proxy_port = os.environ.get("PROXY_PORT")
            if proxy_ip and proxy_port:
                proxy_url = f"http://{proxy_ip}:{proxy_port}"

        data_dir = os.environ.get("DATA_DIR") or _default_data_dir()
        return cls(
            api_key=os.environ.get("API_KEY") or None,
            source=os.environ.get("SOURCE", "checkvisaslots").strip().lower(),
            visa_locations=_env_list("VISA_LOCATIONS", "ISTANBUL"),
            visa_categories=_env_list("VISA_CATEGORIES", "B1/B2"),
            visa_duration_days=_env_int("VISA_DURATION_DAYS", 120),
            require_both_consulate_and_vac=_env_bool(
                "REQUIRE_BOTH_CONSULATE_AND_VAC", False
            ),
            check_interval_minutes=_env_int("CHECK_INTERVAL_MINUTES", 5),
            check_jitter_seconds=_env_int("CHECK_JITTER_SECONDS", 90),
            notify=_env_bool("NOTIFY", True),
            dry_run=_env_bool("DRY_RUN", False),
            telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN") or None,
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID") or None,
            sender_email=os.environ.get("SENDER_EMAIL") or None,
            sender_password=os.environ.get("SENDER_PASSWORD") or None,
            receiver_email=os.environ.get("RECEIVER_EMAIL") or None,
            smtp_host=os.environ.get("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=_env_int("SMTP_PORT", 587),
            smtp_use_tls=_env_bool("SMTP_USE_TLS", True),
            pushover_token=os.environ.get("PUSHOVER_TOKEN") or None,
            pushover_user=os.environ.get("PUSHOVER_USER") or None,
            proxy_url=proxy_url,
            cf_solver_url=os.environ.get("CF_SOLVER_URL") or None,
            request_timeout=_env_int("REQUEST_TIMEOUT", 30),
            impersonate=os.environ.get("CURL_IMPERSONATE", "chrome"),
            data_dir=data_dir,
            dedupe_hours=_env_int("DEDUPE_HOURS", 6),
            health_file=os.environ.get(
                "HEALTH_FILE", f"{data_dir}/last_success.txt"
            ),
            backoff_file=os.environ.get(
                "BACKOFF_FILE", f"{data_dir}/backoff.json"
            ),
            official_email=os.environ.get("OFFICIAL_EMAIL") or None,
            official_password=os.environ.get("OFFICIAL_PASSWORD") or None,
            official_base_url=os.environ.get(
                "OFFICIAL_BASE_URL", "https://www.ustraveldocs.com/tr"
            ),
            checkvisaslots_url=os.environ.get(
                "CHECKVISASLOTS_URL",
                "https://app.checkvisaslots.com/slots/v3",
            ),
            timezone=os.environ.get("TZ", "Asia/Istanbul"),
        )

    @property
    def proxies(self) -> Optional[dict]:
        if not self.proxy_url:
            return None
        # Forward proxies expect http:// scheme for both http and https targets
        return {"http": self.proxy_url, "https": self.proxy_url}

    @property
    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token and self.telegram_chat_id)

    @property
    def has_email(self) -> bool:
        return bool(
            self.sender_email and self.sender_password and self.receiver_email
        )

    @property
    def has_pushover(self) -> bool:
        return bool(self.pushover_token and self.pushover_user)
