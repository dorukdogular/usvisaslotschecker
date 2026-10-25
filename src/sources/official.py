"""Official ustraveldocs.com source stub (Phase 2, default off).

This module intentionally does NOT auto-book appointments. It only sketches
the login + availability probe flow so it can be completed once the
authenticated endpoints are mapped for a real account session.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from ..client import CFSafeClient
from ..config import Config

logger = logging.getLogger(__name__)


class OfficialSourceNotImplemented(NotImplementedError):
    """Raised until authenticated availability endpoints are wired."""


def fetch_official(
    config: Config, client: CFSafeClient
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Probe official site; currently returns a clear stub error.

    Required env when SOURCE=official:
      - OFFICIAL_EMAIL
      - OFFICIAL_PASSWORD
      - CF_SOLVER_URL (strongly recommended; site is Cloudflare-protected)
    """
    if not config.official_email or not config.official_password:
        raise RuntimeError(
            "SOURCE=official requires OFFICIAL_EMAIL and OFFICIAL_PASSWORD"
        )

    logger.warning(
        "Official ustraveldocs source is a Phase-2 stub. "
        "It will not scrape or book appointments yet. "
        "Base URL: %s",
        config.official_base_url,
    )

    # Soft health probe of the public landing page (no credentials sent yet).
    try:
        result = client.get(config.official_base_url)
        logger.info(
            "Official landing probe status=%s via_solver=%s bytes=%s",
            result.status_code,
            result.via_solver,
            len(result.text or ""),
        )
    except Exception as exc:
        logger.error("Official landing probe failed: %s", exc)

    raise OfficialSourceNotImplemented(
        "ustraveldocs authenticated slot endpoints are not wired yet. "
        "Keep SOURCE=checkvisaslots for production. "
        "When ready: implement login cookie jar + availability JSON endpoints "
        "in src/sources/official.py without auto-booking."
    )
