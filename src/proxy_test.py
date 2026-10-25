"""Smoke-test that outbound traffic goes through PROXY_URL."""

from __future__ import annotations

import json
import logging
import os
import sys

from .client import CFSafeClient
from .config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("proxy_test")


def main() -> int:
    config = Config.from_env()
    if not config.proxy_url:
        logger.error(
            "PROXY_URL (or PROXY_IP/PROXY_PORT) is not set — nothing to test"
        )
        return 2

    logger.info("Testing proxy %s", config.proxy_url)
    client = CFSafeClient(config)

    # 1) Echo egress IP via httpbin
    try:
        ip_result = client.get("https://httpbin.org/ip")
        logger.info(
            "httpbin status=%s body=%s",
            ip_result.status_code,
            (ip_result.text or "")[:300],
        )
        if ip_result.status_code != 200:
            logger.error("httpbin request failed")
            return 1
        payload = ip_result.json_data or json.loads(ip_result.text)
        logger.info("Egress IP via proxy: %s", payload.get("origin"))
    except Exception as exc:
        logger.exception("Proxy httpbin test failed: %s", exc)
        return 1

    # 2) Optional checkvisaslots reachability (no API key required for DNS/TLS)
    probe_url = os.environ.get(
        "PROXY_PROBE_URL", "https://app.checkvisaslots.com"
    )
    try:
        probe = client.get(probe_url)
        logger.info(
            "Probe %s status=%s bytes=%s",
            probe_url,
            probe.status_code,
            len(probe.text or ""),
        )
    except Exception as exc:
        logger.warning("Secondary probe failed (non-fatal): %s", exc)

    logger.info("Proxy test OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
