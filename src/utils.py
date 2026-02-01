"""Utility functions for the macOS TTS to Device project."""

import logging
import settings


def setup_logging(level=None, verbose=False):
    """
    Configure logging for the application.

    Args:
        level: Logging level (e.g., "INFO", "DEBUG"). If None, uses settings.LOG_LEVEL.
        verbose: If True, sets level to "INFO" regardless of level argument.
    """
    if verbose:
        log_level = "INFO"
    elif level:
        log_level = level.upper()
    else:
        log_level = settings.LOG_LEVEL

    logging.basicConfig(
        level=getattr(logging, log_level),
        format=settings.LOG_FORMAT,
        datefmt=settings.LOG_DATE_FORMAT,
    )

    return logging.getLogger(__name__)
