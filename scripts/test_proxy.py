#!/usr/bin/env python3
"""Convenience wrapper: python scripts/test_proxy.py"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.proxy_test import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
