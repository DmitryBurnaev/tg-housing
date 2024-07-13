"""
This code snippet defines a Telegram bot using the aiogram library to manage user addresses
in a conversation flow. The bot uses FSMContext to manage the state of the conversation
and provides a structured way for users to interact with address-related commands.
"""

import asyncio
import logging
from logging import config
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from src.config.app import TG_BOT_API_TOKEN
from src.config.logging import LOGGING_CONFIG
from src.db.storage import TGStorage
from src.handlers.bot_handlers import form_router


async def main() -> None:
    """
    Initialize Bot instance with default bot properties which will be passed to all API calls
    """
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.captureWarnings(capture=True)

    bot = Bot(token=TG_BOT_API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
    dp = Dispatcher(storage=TGStorage())
    dp.include_router(form_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
