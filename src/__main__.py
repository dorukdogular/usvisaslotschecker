"""python -m src entrypoint."""

from __future__ import annotations

import argparse
import logging
import sys


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    parser = argparse.ArgumentParser(
        description="Istanbul US Consulate visa slot checker"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="once",
        choices=["once", "loop", "proxy-test"],
        help="once (default), loop, or proxy-test",
    )
    args = parser.parse_args(argv)

    if args.command == "proxy-test":
        from .proxy_test import main as proxy_main

        return proxy_main()

    from .config import Config
    from .runner import run_loop, run_once

    config = Config.from_env()
    if args.command == "loop":
        run_loop(config)
        return 0

    result = run_once(config)
    if result.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
