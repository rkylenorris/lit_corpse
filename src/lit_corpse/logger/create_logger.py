import sys
import loguru
import logging

from functools import lru_cache
from loguru import logger as _base_logger


# --- Intercept standard logging and redirect to Loguru ------------------------


class InterceptHandler(logging.Handler):
    """Redirect standard logging calls into Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _base_logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Forward to Loguru, preserving exception info
        _base_logger.opt(
            depth=6,
            exception=record.exc_info
        ).log(level, record.getMessage())


def intercept_stdlib_logging() -> None:
    """
    Route the stdlib `logging` module logs (used by many libraries) into Loguru.
    This avoids split outputs between two logging systems.
    """
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    for name in logging.root.manager.loggerDict.keys():
        logging.getLogger(name).handlers = [InterceptHandler()]


# --- Create Base logger from Loguru logger

logger = _base_logger


# --- Public configuration function -------------------------------------------


def configure_logging() -> loguru.Logger:
    """configure loguru logger

    Returns:
        loguru.Logger: set up loguru logger
    """

    # Remove all existing sinks
    logger.remove()

    # --- Console Sink (human-friendly) ---
    logger.add(
        sys.stdout,
        level=20,
        colorize=True,
        backtrace=True,
        diagnose=True,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    # --- Rotating File Sink (text) ---
    logger.add(
        "data/app.txt",
        level=10,
        rotation="7 days",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
        enqueue=True,  # safe for multiprocessing
        backtrace=True,
        diagnose=False,
    )

    # --- JSON Structured Logs (optional) ---

    logger.add(
        "data/app.json",
        level=10,
        rotation="7 days",
        retention="30 days",
        encoding="utf-8",
        enqueue=True,
        serialize=True,  # output JSON
    )

    # Route stdlib logging (for libraries) into Loguru
    intercept_stdlib_logging()

    # Bind app_name globally (available in JSON extra) and return logger object
    return logger


@lru_cache(maxsize=1)
def get_logger() -> loguru.Logger:
    """Get the configured logger instance.

    Returns:
        loguru.Logger: configured logger instance
    """
    return configure_logging()