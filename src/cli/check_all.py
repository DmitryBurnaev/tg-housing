"""CLI script to display all users in the database."""

import asyncio
import logging.config
from argparse import ArgumentParser
from collections import defaultdict
from typing import DefaultDict

from aiogram.methods.send_message import SendMessage
from aiogram.types import MessageEntity
from aiogram.utils.formatting import Text, as_key_value, as_marked_section
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config import app as app_config
from src.config import logging as logging_config
from src.config import constants as constants
from src.db.repository import UserRepository
from src.db.session import session_scope
from src.handlers.helpers import SERVICE_NAME_MAP, prepare_entities
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
    repository = UserRepository(session)

    # def prepare_entities() -> list[MessageEntity]:
    #     entities = entities or []
    #     content = as_list(title, *entities, sep="\n\n")
    #     reply_markup = ReplyKeyboardRemove() if reply_keyboard else None
    #
    #     await message.answer(
    #         parse_mode=ParseMode.MARKDOWN,
    #         reply_markup=reply_markup,
    #         **content.as_kwargs(replace_parse_mode=False),
    #     )

    for user_id, shutdowns_by_service in shutdowns.items():
        user = await repository.get(user_id)
        logger.info("Sending shutdowns for %s. Found %i items", user, len(shutdowns_by_service))
        send_entities = prepare_entities(shutdowns_by_service)

        await bot.send_message(
            chat_id=user.chat_id,
            text=f"hi, {user.name}. You have {len(shutdowns_by_service)} shutdowns.",
        )
        # await SendMessage(user.chat_id, "", entities=send_entities)


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
