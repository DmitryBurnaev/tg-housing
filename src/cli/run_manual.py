import argparse
import logging.config
import uuid

from src.config.app import SupportedService, SupportedCity
from src.config.logging import LOGGING_CONFIG
from src.db.models import User
from src.parsing.main_parsing import BaseParser
from src.parsing.spb_services import *

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Process some addresses.")
    parser.add_argument("--address", metavar="address", type=str)
    parser.add_argument("--service", metavar="service", type=str)
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.captureWarnings(capture=True)

    args = parser.parse_args()

    service: SupportedService = SupportedService[args.service]
    user = User(
        id=uuid.uuid4(),
        name="TestUser",
        city=SupportedCity.SPB,
        raw_address=args.address,
    )
    print(BaseParser.get_parsers())
    parser_class = BaseParser.get_parsers()[service]
    service_data_parser = parser_class(city=user.address.city)

    result = service_data_parser.parse(user_address=user.address)
    logger.info(f"Parse Result: \n{result}")
    user.echo_results(result)


if __name__ == "__main__":
    main()
