import os


LOG_LEVEL = os.getenv("LOG_LEVEL", default="DEBUG")
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)s] %(message)s",
            "datefmt": "%d.%m.%Y %H:%M:%S",
        },
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "loggers": {
        "src": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "cli": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "parsing": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "aiogram": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}
