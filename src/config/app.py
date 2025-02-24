"""
Configuration module for the Telegram bot application.

Defines supported cities and services, resource URLs, and loads environment variables
for various application settings.
"""

import enum
import os
from pathlib import Path

from dotenv import load_dotenv


class SupportedCity(enum.StrEnum):
    """Enumeration of cities supported by the utility notification system."""

    SPB = "SPB"
    RND = "RND"


class SupportedService(enum.StrEnum):
    """Enumeration of utility services that can be monitored for maintenance schedules."""

    ELECTRICITY = "ELECTRICITY"
    COLD_WATER = "COLD_WATER"
    HOT_WATER = "HOT_WATER"

    @classmethod
    def members(cls) -> list["SupportedService"]:
        """Return a list of all supported utility services."""
        return [cls.ELECTRICITY, cls.HOT_WATER, cls.COLD_WATER]


PROJECT_PATH = Path(__file__).parent.parent.absolute()
ROOT_PATH = PROJECT_PATH.parent
DATA_PATH = ROOT_PATH / ".data"
os.makedirs(DATA_PATH, exist_ok=True)

ENV_FILE_PATH = ROOT_PATH / ".env"
if ENV_FILE_PATH.exists():
    load_dotenv(ENV_FILE_PATH)  # read env variables from .env

RESOURCE_URLS = {
    SupportedCity.SPB: {
        SupportedService.ELECTRICITY: (
            "https://rosseti-lenenergo.ru/planned_work/?"
            "city={city}&date_start={date_start}&date_finish={date_finish}&street={street_name}"
        ),
        SupportedService.HOT_WATER: (
            "https://www.gptek.spb.ru/grafik/?street={street_name}+{street_prefix}&house={house}"
        ),
        SupportedService.COLD_WATER: "https://www.vodokanal.spb.ru/presscentr/remontnye_raboty/",
    }
}

CITY_NAME_MAP = {
    SupportedCity.SPB: "Санкт-Петербург",
}

# Bot token can be obtained via https://t.me/BotFather
TG_BOT_API_TOKEN = os.getenv("TG_BOT_API_TOKEN")
TG_TEST_USERS_LIST = os.getenv("TG_TEST_USERS_LIST", "").split(",")
TG_TEST_CHAT_IDS = os.getenv("TG_TEST_CHAT_IDS", "").split(",")

TMP_DATA_DIR = PROJECT_PATH.parent / ".data"

DEBUG_SHUTDOWNS = os.getenv("DEBUG_SHUTDOWNS", "false").lower() == "true"

SSL_REQUEST_VERIFY = os.getenv("SSL_REQUEST_VERIFY", "true").lower() == "true"

LOCALE = os.getenv("LOCALE", "ru-RU").lower()
I18N_FALLBACK = os.getenv("I18N_FALLBACK", "false").lower() == "false"

# SQLite database URL for async connection
DATABASE_URL = f"sqlite:///{DATA_PATH}/database.db"
DATABASE_URL_ASYNC = f"sqlite+aiosqlite:///{DATA_PATH}/database.db"
