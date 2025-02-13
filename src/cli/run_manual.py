import argparse
import logging.config
import pprint
import uuid
from typing import cast

from src.config.app import SupportedCity, SupportedService
from src.config.logging import LOGGING_CONFIG
from src.db.old_models import User
from src.parsing.main_parsing import BaseParser

logger = logging.getLogger("cli.run_manual")


def main() -> None:
    parser = argparse.ArgumentParser(description="Process some addresses.")
    parser.add_argument("--address", metavar="address", type=str)
    parser.add_argument("--service", metavar="service", type=str)
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.captureWarnings(capture=True)

    args = parser.parse_args()
    request_service: str = args.service
    if request_service.upper() not in SupportedService.members():
        logger.error(f"Unsupported service: {request_service}")
        return

    service: SupportedService = cast(SupportedService, SupportedService[request_service.upper()])
    user = User(
        id=uuid.uuid4(),
        name="TestUser",
        city=SupportedCity.SPB,
        raw_address=args.address,
    )
    parser_class = BaseParser.get_parsers()[service]
    if not user.address:
        logger.info("User has no address, skip checking!")
        return

    service_data_parser = parser_class(city=user.address.city)
    result = service_data_parser.parse(user_address=user.address)
    logger.info("Parse Result")
    pprint.pp(result, indent=4)
    user.echo_results(result)


if __name__ == "__main__":
    main()
