import enum
import os
from pathlib import Path

from dotenv import load_dotenv


class SupportedCity(enum.StrEnum):
    SPB = "SPB"
    RND = "RND"


class SupportedService(enum.StrEnum):
    ELECTRICITY = "ELECTRICITY"
    COLD_WATER = "COLD_WATER"
    HOT_WATER = "HOT_WATER"

    @classmethod
    def members(cls) -> list["SupportedService"]:
        # TODO: use correct logic: list(map(lambda x: x.value, cls))
        return [cls.ELECTRICITY]


PROJECT_PATH = Path(__file__).parent.parent.absolute()
ROOT_PATH = PROJECT_PATH.parent
DATA_PATH = ROOT_PATH / ".data"
os.makedirs(DATA_PATH, exist_ok=True)

ENV_FILE_PATH = ROOT_PATH / ".env"
if ENV_FILE_PATH.exists():
    load_dotenv(ENV_FILE_PATH)  # read env variables from .env

RESOURCE_URLS = {
    SupportedCity.SPB: {
        SupportedService.ELECTRICITY: "https://rosseti-lenenergo.ru/planned_work/?city={city}&date_start={date_start}&date_finish={date_finish}&street={street_name}",
        SupportedService.HOT_WATER: "https://www.gptek.spb.ru/grafik/?street={street_name}+{street_prefix}&house={house}",
        SupportedService.COLD_WATER: "https://www.vodokanal.spb.ru/presscentr/remontnye_raboty/",
    }
}

CITY_NAME_MAP = {
    SupportedCity.SPB: "Санкт-Петербург",
}

SERVICE_NAME_MAP = {
    SupportedService.ELECTRICITY: "💡Electricity",
    SupportedService.COLD_WATER: "︎🚰 Cold Water",
    SupportedService.HOT_WATER: "🚿 Hot Water",
}

# Bot token can be obtained via https://t.me/BotFather
TG_BOT_API_TOKEN = os.getenv("TG_BOT_API_TOKEN")
TG_TEST_USERS_LIST = os.getenv("TG_TEST_USERS_LIST", "").split(",")
TG_TEST_CHAT_IDS = os.getenv("TG_TEST_CHAT_IDS", "").split(",")

TMP_DATA_DIR = PROJECT_PATH.parent / ".data"

DEBUG_SHUTDOWNS = os.getenv("DEBUG_SHUTDOWNS", "false").lower() == "true"

SSL_REQUEST_VERIFY = os.getenv("SSL_REQUEST_VERIFY", "true").lower() == "true"
