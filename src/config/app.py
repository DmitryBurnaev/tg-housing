"""
Configuration module for the Telegram bot application.

Defines supported cities and services, resource URLs, and loads environment variables
for various application settings.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_PATH = Path(__file__).parent.parent.absolute()
ROOT_PATH = PROJECT_PATH.parent
DATA_PATH = ROOT_PATH / ".data"
DATA_PATH.mkdir(parents=True, exist_ok=True)
SITES_CACHE_PATH = DATA_PATH / "sites"
SITES_CACHE_PATH.mkdir(parents=True, exist_ok=True)

ENV_FILE_PATH = ROOT_PATH / ".env"
if ENV_FILE_PATH.exists():
    load_dotenv(ENV_FILE_PATH)  # read env variables from .env

# Bot token can be obtained via https://t.me/BotFather
TG_BOT_API_TOKEN = os.getenv("TG_BOT_API_TOKEN", "")
TG_TEST_USERS_LIST = os.getenv("TG_TEST_USERS_LIST", "").split(",")
TG_TEST_CHAT_IDS = os.getenv("TG_TEST_CHAT_IDS", "").split(",")

DEBUG_SHUTDOWNS: bool = os.getenv("PARSE_DEBUG_SHUTDOWNS", "false").lower() == "true"
PARSE_DAYS_BEFORE: int = int(os.getenv("PARSE_DAYS_BEFORE", "1"))
PARSE_DAYS_AFTER: int = int(os.getenv("PARSE_DAYS_AFTER", "90"))

SSL_REQUEST_VERIFY = os.getenv("SSL_REQUEST_VERIFY", "true").lower() == "true"

LOCALE = os.getenv("LOCALE", "ru-RU").lower()
LOCALE_PATH = PROJECT_PATH / "i18n"
I18N_FALLBACK = os.getenv("I18N_FALLBACK", "false").lower() == "false"
DT_FORMAT = "%d.%m.%Y %H:%M"
D_FORMAT = "%d.%m.%Y"

# SQLite database URL for async connection
DATABASE_URL = f"sqlite:///{DATA_PATH}/database.db"
DATABASE_URL_ASYNC = f"sqlite+aiosqlite:///{DATA_PATH}/database.db"

MAPPING_STRING_REPLACEMENT: dict[str, str] = {}
for _mapping in os.getenv("PREFIX_STREET_REPLACEMENT", "").split(";"):
    # creating mapping like: 'StreetName' -> 'av'
    if _mapping:
        key, value = _mapping.split(":")
        MAPPING_STRING_REPLACEMENT[key] = value
