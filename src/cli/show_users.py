"""CLI script to display all users in the database."""

import asyncio
import logging.config

from aiogram.utils.formatting import Text, as_key_value, as_marked_section
from sqlalchemy.ext.asyncio import AsyncSession

from src.i18n import _
from src.config.app import SupportedCity
from src.db.repository import UserRepository
from src.config.logging import LOGGING_CONFIG
from src.db.session import session_scope
from src.handlers.helpers import DT_FORMAT, SERVICE_NAME_MAP
from src.providers.shutdowns import ShutDownByServiceInfo, ShutDownProvider

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


async def find_shutdowns(addresses: list[str]) -> list[Text]:
    """Using fetch_shutdowns find possible shutdowns for user's addresses"""

    shutdowns_by_service: list[ShutDownByServiceInfo] = ShutDownProvider.for_addresses(
        addresses
    )
    if not shutdowns_by_service:
        return [Text(_("No shutdowns :)"))]

    result: list[Text] = []
    for shutdown_by_service in shutdowns_by_service:
        if not shutdown_by_service.shutdowns:
            continue

        title = SERVICE_NAME_MAP[shutdown_by_service.service]
        values = []
        for shutdown_info in shutdown_by_service.shutdowns:
            values.append(
                as_marked_section(
                    shutdown_info.raw_address,
                    as_key_value(_("Start"), shutdown_info.start.strftime(DT_FORMAT)),
                    as_key_value(_("End"), shutdown_info.end.strftime(DT_FORMAT)),
                    marker="   - ",
                )
            )

        result.append(as_marked_section(title, *values, marker=" ⚠︎ "))

    return result


async def show_users(session: AsyncSession) -> None:
    """Fetch and display all users from the database."""

    repository = UserRepository(session)
    users = await repository.get_list(city=SupportedCity.SPB)
    if not users:
        logger.info("No users found in database")
        return

    logger.info("Current users in database:")
    for user in users:
        logger.info("ID: %d, Telegram ID: %d, User: %s", user.id, user, user.name)
        # Print addresses for this user
        if user.addresses:
            for addr in user.addresses:
                logger.info("\tAddress: %s, City: %s", addr.address, addr.city)
        else:
            logger.info("\tNo addresses registered")


async def main() -> None:
    """Main entry point for the CLI script."""
    async with session_scope() as session:
        await show_users(session)


if __name__ == "__main__":
    asyncio.run(main())
