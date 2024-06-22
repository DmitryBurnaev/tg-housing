import asyncio
import logging
import sys
from os import getenv

from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    ReplyKeyboardRemove,
)

TOKEN = getenv("BOT_TOKEN")

form_router = Router()


class UserAddressStatesGroup(StatesGroup):
    add_address = State()


@form_router.message(Command("address"))
async def command_address(message: Message, state: FSMContext) -> None:
    """
    Transition to state "set_address"
    """
    await state.set_state(UserAddressStatesGroup.add_address)
    await message.answer(
        "Hi there! What's your address?",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Command("cancel"))
@form_router.message(F.text.casefold() == "cancel")
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logging.info("Cancelling state %r", current_state)
    await state.set_state(state=None)
    await message.answer("Cancelled.", reply_markup=ReplyKeyboardRemove())


@form_router.message(Command("info"))
async def info_handler(message: Message, state: FSMContext) -> None:
    """
    Allow user to cancel any action
    """
    data = await state.get_data()

    echo_addresses = "\n - ".join(data.get("addresses", []))
    await message.answer(
        f"Hi, {html.bold(message.from_user.full_name)}!`\n`"
        f"I remember your address:\n - {echo_addresses}",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(UserAddressStatesGroup.add_address)
async def add_address(message: Message, state: FSMContext) -> None:
    new_address: str = message.text
    state_data = await state.get_data()
    addresses = state_data.get("address", None) or []
    addresses.append(new_address)
    echo_addresses = "\n - ".join(addresses)
    await state.update_data(address=addresses)
    await state.set_state(state=None)
    await message.answer(
        f"Ok, I'll remember your address, {html.bold(message.from_user.full_name)}!\n - {echo_addresses}",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Command("clear"))
async def clear_handler(message: Message, state: FSMContext) -> None:
    """
    Allow user to cancel any action
    """
    await state.clear()
    await message.answer(
        f"Ok, I forgot all for you, {html.bold(message.from_user.full_name)}!",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Command("shutdowns"))
async def shutdowns_handler(message: Message, state: FSMContext) -> None:
    """
    Allow user to cancel any action
    """
    data = await state.get_data()
    echo_addresses = "\n - ".join(data.get("addresses", []))
    await message.answer(
        f"Ok, I'll return future shutdowns for your addresses:\n - {echo_addresses}",
        reply_markup=ReplyKeyboardRemove(),
    )


async def main() -> None:
    """
    Initialize Bot instance with default bot properties which will be passed to all API calls
    """
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(form_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
