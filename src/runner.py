"""Main check + optional long-running loop with jitter and backoff."""

from __future__ import annotations

import json
import logging
import os
import random
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from .checker import filter_slots, summarize_activity
from .client import BackoffController, CFSafeClient, CloudflareBlockedError
from .config import Config
from .dedupe import DedupeStore
from .notify import notify_all
from .sources import fetch_slots

logger = logging.getLogger(__name__)


def _write_health(path: str, timezone_name: str = "Asia/Istanbul") -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = ZoneInfo("Asia/Istanbul")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(datetime.now(tz=tz).isoformat())


def _log_unique_locations(slots: List[Dict[str, Any]]) -> None:
    locations = sorted(
        {
            str(s.get("visa_location", "")).strip()
            for s in slots
            if s.get("visa_location")
        }
    )
    logger.info("API visa_location values (%s): %s", len(locations), locations)


def adaptive_interval_seconds(
    config: Config, remaining: Optional[int]
) -> int:
    base = max(1, config.check_interval_minutes) * 60
    jitter = random.randint(0, max(0, config.check_jitter_seconds))
    extra = 0
    if remaining is not None:
        if remaining <= 5:
            extra = 45 * 60
            logger.warning(
                "API remaining=%s — extending interval by 45 minutes",
                remaining,
            )
        elif remaining <= 20:
            extra = 15 * 60
            logger.warning(
                "API remaining=%s — extending interval by 15 minutes",
                remaining,
            )
    return base + jitter + extra


def run_once(config: Optional[Config] = None) -> Dict[str, Any]:
    config = config or Config.from_env()
    os.makedirs(config.data_dir, exist_ok=True)

    backoff = BackoffController(config.backoff_file)
    wait = backoff.should_wait()
    if wait > 0:
        logger.warning("Still in backoff — skipping run (%.0fs left)", wait)
        return {"skipped": True, "backoff_remaining": wait}

    # Optional pre-jitter when invoked from cron (one-shot mode)
    if os.environ.get("ONESHOT_JITTER", "true").lower() in {
        "1",
        "true",
        "yes",
    } and os.environ.get("RUN_MODE", "once") == "once":
        jitter = random.randint(0, max(0, config.check_jitter_seconds))
        if jitter:
            logger.info("Pre-check jitter sleep %ss", jitter)
            time.sleep(jitter)

    client = CFSafeClient(config)
    dedupe = DedupeStore(
        os.path.join(config.data_dir, "last_alert.json"),
        ttl_hours=config.dedupe_hours,
    )

    try:
        slots, raw = fetch_slots(config, client)
    except CloudflareBlockedError as exc:
        minutes = backoff.record_failure()
        logger.error("Blocked by protection: %s (backoff %sm)", exc, minutes)
        return {"error": str(exc), "backoff_minutes": minutes}
    except Exception as exc:
        # Auth / config errors should not trigger long CF-style backoff
        msg = str(exc)
        if "Invalid Access" in msg or "HTTP 400" in msg or "HTTP 401" in msg:
            logger.error("Fetch failed (no backoff): %s", exc)
            return {"error": msg, "backoff_minutes": 0}
        minutes = backoff.record_failure()
        logger.exception("Fetch failed: %s", exc)
        return {"error": msg, "backoff_minutes": minutes}

    remaining = None
    if raw:
        remaining, activity_msg = summarize_activity(raw)
        logger.info(activity_msg)
        _log_unique_locations(slots)

    matched = filter_slots(slots, config)
    logger.info(
        "Matched %s slot(s) for locations=%s categories=%s",
        len(matched),
        config.visa_locations,
        config.visa_categories,
    )

    if matched:
        logger.info("Matched slots:\n%s", json.dumps(matched, indent=2, default=str))
        fresh = dedupe.filter_new(matched)
        if fresh:
            notify_all(fresh, config)
            dedupe.mark_alerted(fresh)
            logger.info("Alerted on %s new slot(s)", len(fresh))
        else:
            logger.info("All matched slots already alerted within dedupe window")
    else:
        logger.info(
            "No relevant slots within %s days",
            config.visa_duration_days,
        )

    backoff.record_success()
    _write_health(config.health_file, config.timezone)
    return {
        "matched": matched,
        "remaining": remaining,
        "total_slots": len(slots),
    }


def run_loop(config: Optional[Config] = None) -> None:
    """Long-running process with interval + jitter (preferred over fixed cron)."""
    config = config or Config.from_env()
    # Disable one-shot jitter inside loop — loop handles timing itself
    os.environ["RUN_MODE"] = "loop"
    logger.info(
        "Starting loop interval=%sm jitter=0-%ss source=%s",
        config.check_interval_minutes,
        config.check_jitter_seconds,
        config.source,
    )
    while True:
        result = run_once(config)
        remaining = None
        if isinstance(result, dict):
            remaining = result.get("remaining")
            if result.get("skipped") and result.get("backoff_remaining"):
                time.sleep(min(result["backoff_remaining"], 60))
                continue
            if result.get("backoff_minutes"):
                time.sleep(int(result["backoff_minutes"]) * 60)
                continue
        sleep_for = adaptive_interval_seconds(config, remaining)
        logger.info("Sleeping %ss until next check", sleep_for)
        time.sleep(sleep_for)
