import argparse
import logging.config
import uuid

from src.config.app import SupportedService, SupportedCity
from src.config.logging import LOGGING_CONFIG
from src.db.models import User
from src.parsing.main_parsing import BaseParser

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Process some addresses.")
    parser.add_argument("address", metavar="address", type=str)
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.captureWarnings(capture=True)

    args = parser.parse_args()

    user = User(
        id=uuid.uuid4(),
        name="TestUser",
        city=SupportedCity.SPB,
        raw_address=args.address,
    )
    service_data_parser = BaseParser(city=user.address.city)
    result = service_data_parser.parse(SupportedService.ELECTRICITY, user_address=user.address)
    logger.info(f"Parse Result: \n{result}")
    user.send_notification(result)


if __name__ == "__main__":
    main()
