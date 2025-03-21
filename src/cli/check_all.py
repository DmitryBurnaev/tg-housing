"""CLI script to display all users in the database."""

import asyncio
import logging.config
from typing import DefaultDict
from collections import defaultdict
from argparse import ArgumentParser, ONE_OR_MORE

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.utils.formatting import as_list
from aiogram.client.default import DefaultBotProperties
from sqlalchemy.ext.asyncio import AsyncSession

from src.i18n import _
from src.config.app import TG_BOT_API_TOKEN
from src.config.logging import LOGGING_CONFIG
from src.config import constants as constants
from src.db.repository import UserRepository
from src.db.session import session_scope
from src.handlers.helpers import prepare_entities
from src.providers.shutdowns import ShutDownByServiceInfo, ShutDownProvider

logger = logging.getLogger("cli")


async def get_shutdowns_per_user(
    session: AsyncSession, user_ids: list[int] | None = None
) -> dict[int, list[ShutDownByServiceInfo]]:
    """Fetch and display all users from the database."""

    user_repository = UserRepository(session)
    users = await user_repository.filter(ids=user_ids)
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
            addresses = await user_repository.get_addresses_plain(user.id, city)
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
        if not shutdowns_by_service:
            logger.info("No shutdowns found for user: '%s'", user)
            continue

        logger.info("Sending shutdowns for %s. Found %i items", user, len(shutdowns_by_service))
        send_entities = prepare_entities(shutdowns_by_service)
        title = _("Hi! \nI've detected some information:").format(full_name=user.name)
        content = as_list(title, *send_entities, sep="\n\n")
        string_content: str = content.as_pretty_string()
        already_sent = await user_repository.has_notification(user.id, string_content)
        if already_sent:
            logger.info("Sending notification already exists for user: '%s' (SKIP)", user)
            continue

        await bot.send_message(
            chat_id=user.chat_id,
            **content.as_kwargs(replace_parse_mode=False),
        )
        await user_repository.add_notification(user.id, string_content)


def create_parser() -> ArgumentParser:
    """Get values from user's input"""
    parser = ArgumentParser()
    parser.add_argument("--user-ids", type=int, nargs=ONE_OR_MORE, help="Target user ids")
    return parser


async def main() -> None:
    """
    Main function for fetching shutdowns for each user in DB,
    preparing messages and sending to chats.
    """
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.captureWarnings(capture=True)

    parser = create_parser()
    ns = parser.parse_args()

    if not TG_BOT_API_TOKEN:
        logger.error("TG bot API token (env `TG_BOT_API_TOKEN`)  not provided")
        exit(1)

    if ns.user_ids:
        logger.info("Fetching shutdowns for users: %s", ns.user_ids)
    else:
        logger.info("Fetching shutdowns for all users in DB")

    async with (
        session_scope() as session,
        Bot(
            token=TG_BOT_API_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
        ) as bot,
    ):
        shutdowns = await get_shutdowns_per_user(session, user_ids=ns.user_ids)
        await send_shutdowns(bot, session, shutdowns)


if __name__ == "__main__":
    asyncio.run(main())
