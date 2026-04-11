import logging
import logging.config
import os


def setup_logging() -> None:
    """Configure logging for the entire application."""
    level = os.getenv("LOG_LEVEL", "INFO").upper()

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "level": level,
            },
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
    }
    logging.config.dictConfig(config)
