"""Logging configuration."""

from __future__ import annotations

import logging
import sys


def configure_logging() -> None:
    """Configure application logging."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )