"""Cloudflare-aware HTTP client using curl_cffi (+ optional FlareSolverr)."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from curl_cffi import requests as cffi_requests

from .config import Config

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
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


@dataclass
class HttpResult:
    status_code: int
    text: str
    json_data: Optional[Any] = None
    headers: Optional[Dict[str, str]] = None
    via_solver: bool = False


class CloudflareBlockedError(Exception):
    """Raised when a Cloudflare challenge or hard block is detected."""

    def __init__(self, status_code: int, body_snippet: str):
        self.status_code = status_code
        self.body_snippet = body_snippet
        super().__init__(
            f"Cloudflare/bot protection blocked request "
            f"(status={status_code}): {body_snippet[:200]}"
        )


def _looks_like_cloudflare(status_code: int, text: str) -> bool:
    if status_code in {403, 503, 429}:
        lowered = (text or "").lower()
        markers = (
            "cloudflare",
            "cf-ray",
            "attention required",
            "just a moment",
            "enable javascript",
            "checking your browser",
            "challenge-platform",
        )
        if any(m in lowered for m in markers):
            return True
        if status_code in {403, 503} and "<html" in lowered:
            return True
    return False


class CFSafeClient:
    """HTTP client that impersonates Chrome TLS and can fall back to FlareSolverr."""

    def __init__(self, config: Config):
        self.config = config
        self.session = cffi_requests.Session(impersonate=config.impersonate)

    def get(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> HttpResult:
        merged = dict(DEFAULT_HEADERS)
        if headers:
            merged.update(headers)

        try:
            response = self.session.get(
                url,
                headers=merged,
                params=params,
                proxies=self.config.proxies,
                timeout=self.config.request_timeout,
                verify=True,
            )
        except Exception as exc:
            logger.warning("Direct request failed: %s", exc)
            if self.config.cf_solver_url:
                return self._via_flaresolverr(url, merged)
            raise

        text = response.text or ""
        if _looks_like_cloudflare(response.status_code, text):
            logger.warning(
                "Cloudflare-like response status=%s; trying solver if configured",
                response.status_code,
            )
            if self.config.cf_solver_url:
                return self._via_flaresolverr(url, merged)
            raise CloudflareBlockedError(response.status_code, text)

        json_data = None
        try:
            json_data = response.json()
        except Exception:
            json_data = None

        return HttpResult(
            status_code=response.status_code,
            text=text,
            json_data=json_data,
            headers=dict(response.headers),
            via_solver=False,
        )

    def post(
        self,
        url: str,
        *,
        data: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> HttpResult:
        merged = {"accept": "*/*"}
        if headers:
            merged.update(headers)

        response = self.session.post(
            url,
            data=data,
            json=json_body,
            headers=merged,
            proxies=self.config.proxies,
            timeout=self.config.request_timeout,
            verify=True,
        )
        text = response.text or ""
        json_data = None
        try:
            json_data = response.json()
        except Exception:
            json_data = None
        return HttpResult(
            status_code=response.status_code,
            text=text,
            json_data=json_data,
            headers=dict(response.headers),
        )

    def _via_flaresolverr(
        self, url: str, headers: Dict[str, str]
    ) -> HttpResult:
        solver = self.config.cf_solver_url.rstrip("/")
        payload = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000,
        }
        if self.config.proxy_url:
            payload["proxy"] = {"url": self.config.proxy_url}

        logger.info("Fetching via FlareSolverr at %s", solver)
        # Solver itself is usually local — do not send through external proxy
        response = self.session.post(
            f"{solver}/v1",
            json=payload,
            timeout=90,
            verify=True,
        )
        data = response.json()
        if data.get("status") != "ok":
            raise CloudflareBlockedError(
                response.status_code,
                json.dumps(data)[:500],
            )
        solution = data.get("solution") or {}
        body = solution.get("response") or ""
        status = int(solution.get("status") or 200)
        json_data = None
        try:
            json_data = json.loads(body)
        except Exception:
            json_data = None
        return HttpResult(
            status_code=status,
            text=body,
            json_data=json_data,
            headers=solution.get("headers") or {},
            via_solver=True,
        )


class BackoffController:
    """Persists exponential backoff state across process restarts."""

    def __init__(self, path: str, max_minutes: int = 60):
        self.path = path
        self.max_minutes = max_minutes
        self._minutes = 0
        self._until = 0.0
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._minutes = int(data.get("minutes", 0))
            self._until = float(data.get("until", 0))
        except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
            self._minutes = 0
            self._until = 0.0

    def _save(self) -> None:
        import os

        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(
                {"minutes": self._minutes, "until": self._until},
                fh,
            )

    def should_wait(self) -> float:
        """Return remaining wait seconds, or 0 if clear to proceed."""
        remaining = self._until - time.time()
        return max(0.0, remaining)

    def record_success(self) -> None:
        self._minutes = 0
        self._until = 0.0
        self._save()

    def record_failure(self) -> int:
        if self._minutes <= 0:
            self._minutes = 15
        else:
            self._minutes = min(self._minutes * 2, self.max_minutes)
        self._until = time.time() + self._minutes * 60
        self._save()
        logger.warning("Backoff engaged for %s minutes", self._minutes)
        return self._minutes
