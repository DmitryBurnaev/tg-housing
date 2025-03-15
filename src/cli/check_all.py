"""CLI script to display all users in the database."""

import asyncio
import logging.config
from typing import DefaultDict
from collections import defaultdict

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.utils.formatting import as_list
from aiogram.client.default import DefaultBotProperties
from sqlalchemy.ext.asyncio import AsyncSession

from src.i18n import _
from src.config import app as app_config
from src.config import logging as logging_config
from src.config import constants as constants
from src.db.repository import UserRepository
from src.db.session import session_scope
from src.handlers.helpers import prepare_entities
from src.providers.shutdowns import ShutDownByServiceInfo, ShutDownProvider

logging.config.dictConfig(logging_config.LOGGING_CONFIG)
logger = logging.getLogger(__name__)


async def get_shutdowns_per_user(session: AsyncSession) -> dict[int, list[ShutDownByServiceInfo]]:
    """Fetch and display all users from the database."""

    repository = UserRepository(session)
    users = await repository.all()
    if not users:
        logger.info("No users found in database")
        return {}

    def fetch_for_user(
        user_id: int, city: constants.SupportedCity, addresses: list[str]
    ) -> dict[int, list[ShutDownByServiceInfo]]:
        shutdowns_by_service = ShutDownProvider.for_addresses(city, addresses)
        return {user_id: shutdowns_by_service}

    logger.info("Current users in database:")
    tasks = []
    for user in users:
        logger.info(" ==> ID: %d, Chat ID: %d, User: %s <==", user.id, user.chat_id, user.name)
        for city in constants.SupportedCity:
            logger.info(f"Finding shutdowns for {city.name}: {user.id}")
            addresses = await repository.get_addresses_plain(user.id, city)
            tasks.append(
                asyncio.to_thread(
                    fetch_for_user,
                    user_id=user.id,
                    city=city,
                    addresses=addresses,
                )
            )

    result: DefaultDict[int, list[ShutDownByServiceInfo]] = defaultdict(list)
    fetched_results: list[dict[int, list[ShutDownByServiceInfo]]] = await asyncio.gather(*tasks)
    for fetched_result in fetched_results:
        for user_id, shutdowns_by_service in fetched_result.items():
            result[user_id].extend(shutdowns_by_service)

    return result


async def send_shutdowns(
    bot: Bot, session: AsyncSession, shutdowns: dict[int, list[ShutDownByServiceInfo]]
) -> None:
    """Prepares and send found shutdowns to TG's chats (related to stored users)"""

    user_repository = UserRepository(session)

    for user_id, shutdowns_by_service in shutdowns.items():
        user = await user_repository.get(user_id)
        logger.info("Sending shutdowns for %s. Found %i items", user, len(shutdowns_by_service))
        send_entities = prepare_entities(shutdowns_by_service)
        title = _(
            "Hi, {user}. I've detected some shutdowns for your addresses:".format(user=user.name)
        )
        content = as_list(title, *send_entities, sep="\n\n")

        await bot.send_message(
            chat_id=user.chat_id,
            **content.as_kwargs(replace_parse_mode=False),
        )


#
# def create_parser() -> ArgumentParser:
#     parser = ArgumentParser()
#     parser.add_argument("--token", help="Telegram Bot API Token")
#     parser.add_argument("--chat-id", type=int, help="Target chat id")
#     parser.add_argument("--message", "-m", help="Message text to sent", default="Hello, World!")
#
#     return parser


async def main() -> None:
    """
    Main function for fetching shutdowns for each user in DB,
    preparing messages and sending to chats.
    """

    token = app_config.TG_BOT_API_TOKEN
    if not token:
        logger.error("TG bot API token (env `TG_BOT_API_TOKEN`)  not provided")
        exit(1)

    async with (
        session_scope() as session,
        Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
        ) as bot,
    ):
        shutdowns = await get_shutdowns_per_user(session)
        await send_shutdowns(bot, session, shutdowns)


if __name__ == "__main__":
    asyncio.run(main())
