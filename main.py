"""Application entry point for the Phase 0 bootstrap."""

import sys

from loguru import logger

from krithika.config import KrithikaConfig


def main() -> None:
    """Validate configuration and report that bootstrap setup is ready."""

    config = KrithikaConfig()
    logger.remove()
    logger.add(sys.stderr, level=config.log_level)
    logger.info("Krithika is configured; voice features will be added in later phases.")


if __name__ == "__main__":
    main()
