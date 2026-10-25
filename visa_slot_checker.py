#!/usr/bin/env python3
"""Thin entrypoint kept for back-compat with existing cron/Docker setup."""

from __future__ import annotations

import os
import sys

# Ensure package imports work when executed as a script from /app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.__main__ import main  # noqa: E402


if __name__ == "__main__":
    # Default: one-shot check (cron / supervisord loop both supported)
    command = os.environ.get("RUN_MODE", "once")
    if command not in {"once", "loop", "proxy-test"}:
        command = "once"
    raise SystemExit(main([command]))
