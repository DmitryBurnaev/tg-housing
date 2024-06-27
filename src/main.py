"""
This code snippet defines a Telegram bot using the aiogram library to manage user addresses
in a conversation flow. The bot uses FSMContext to manage the state of the conversation
and provides a structured way for users to interact with address-related commands.
"""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton

from src.config.app import TG_BOT_API_TOKEN

form_router = Router()


class UserAddressStatesGroup(StatesGroup):
    """
    Represents the states group for managing user addresses in the conversation flow.

    States:
        - address: State representing the initial address state.
        - add_address: State representing the state when the user wants to add an address.
        - remove_address: State representing the state when the user wants to remove an address.
    """

    address = State()
    add_address = State()
    remove_address = State()


@form_router.message(Command("address"))
async def command_address(message: Message, state: FSMContext) -> None:
    """
    Transition to state "set_address"
    """
    await state.set_state(UserAddressStatesGroup.address)
    await message.answer(
        "What do you want?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text="Add Address"),
                    KeyboardButton(text="Remove Address"),
                ]
            ],
            resize_keyboard=True,
        ),
    )


@form_router.message(UserAddressStatesGroup.address, F.text.casefold() == "add address")
async def add_address_command(message: Message, state: FSMContext) -> None:
    """
    Handle the 'add address' command from the user.
    Transition the user's state to 'add_address' state.

    Args:
        message (Message): The message object representing the user's input.
        state (FSMContext): The state context for the user.

    Returns:
        None
    """
    await state.set_state(UserAddressStatesGroup.add_address)
    await message.answer(
        "Ok, Sent me your address (without city, default - SPB)",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(UserAddressStatesGroup.address, F.text.casefold() == "remove address")
async def remove_address_command(message: Message, state: FSMContext) -> None:
    """
    Handle the "remove address" command from the user.
    Update the state to 'remove_address' and prompt the user to select an address to remove.
    In order to allow the user to select an address,
    the addresses are displayed as keyboard buttons.

    Args:
        message (Message): The message object representing the user's input.
        state (FSMContext): The FSMContext object to manage the state of the conversation.

    Returns:
        None
    """
    state_data = await state.get_data()
    await state.set_state(UserAddressStatesGroup.remove_address)
    await message.answer(
        "What address do you want to remove?",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text=address) for address in state_data.get("address", None) or []]
            ],
            resize_keyboard=True,
        ),
    )


@form_router.message(UserAddressStatesGroup.add_address)
async def add_address_handler(message: Message, state: FSMContext) -> None:
    """
    Handles the user input for adding a new address during the conversation flow.

    Parameters:
        - message (Message): The message object containing the user input.
        - state (FSMContext): The FSMContext object to manage the conversation state.

    Returns:
        None
    """
    new_address: str = message.text
    state_data = await state.get_data()
    addresses = state_data.get("address", None) or []
    addresses.append(new_address)
    await state.update_data(address=addresses)
    await state.set_state(state=None)

    echo_addresses = await _fetch_addresses(state)
    await message.answer(
        f"Ok, I'll remember your address, {html.bold(message.from_user.full_name)}! "
        f"{echo_addresses}",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(UserAddressStatesGroup.remove_address)
async def remove_address_handler(message: Message, state: FSMContext) -> None:
    """
    Handle the removal of an address from the user's list of addresses.
    Function removes the specified address from the user's list stored in the conversation state.
    It updates the state data accordingly and sends a confirmation message to the user.

    Parameters:
        - message (Message): The message object triggering the handler.
        - state (FSMContext): The current state of the conversation flow.

    Returns:
        None

    """
    state_data = await state.get_data()
    new_addresses: list[str] = [
        address for address in state_data.get("address", None) or [] if address != message.text
    ]
    await state.update_data(address=new_addresses)
    # await state.set_state(None)

    echo_addresses = await _fetch_addresses(state)
    await message.answer(
        f"OK. Address '{message.text}' was removed!{echo_addresses}",
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
    Handles showing user's current address and other common information
    Parameters:
        - message (Message): The message object.
        - state (FSMContext): The current state of the conversation.

    Returns:
        None
    """
    echo_addresses = await _fetch_addresses(state)
    if echo_addresses:
        msg = echo_addresses
    else:
        msg = "I don't remember any your address. Could you add a first one?"

    await message.answer(
        f"Hi, {html.bold(message.from_user.full_name)}!\n{msg}",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(UserAddressStatesGroup.add_address)
async def add_address(message: Message, state: FSMContext) -> None:
    """
    Handles the user input to add a new address to the conversation flow.

    Parameters:
        - message (Message): The message object containing the user input.
        - state (FSMContext): The state context to manage the conversation flow.

    Returns:
        None
    """
    new_address: str = message.text
    state_data = await state.get_data()
    addresses = state_data.get("address", None) or []
    addresses.append(new_address)
    await state.update_data(address=addresses)
    # TODO: fix missed state saving
    # await state.set_state(state=None)

    echo_addresses = await _fetch_addresses(state)
    await message.answer(
        f"Ok, I'll remember your address, {html.bold(message.from_user.full_name)}! "
        f"{echo_addresses}",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Command("clear"))
async def clear_handler(message: Message, state: FSMContext) -> None:
    """
    This handler clears the state of the conversation and sends a message to the user
    indicating that all data has been forgotten.

    Parameters:
        - message (Message): The message object triggering the handler
        - state (FSMContext): The current state of the conversation

    Returns:
        - None

    """
    await state.clear()
    await message.answer(
        f"Ok, I forgot all for you, {html.bold(message.from_user.full_name)}!",
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(Command("shutdowns"))
async def shutdowns_handler(message: Message, state: FSMContext) -> None:
    """
    Handle the 'shutdowns' command by fetching addresses from the current state and
    sending a response message to the user.

    Parameters:
        - message (Message): The message object triggering the command.
        - state (FSMContext): The current state of the conversation.

    Returns:
        - None
    """
    echo_addresses = await _fetch_addresses(state)
    shutdowns = await _fetch_shutdowns()
    await message.answer(
        f"Ok, That's your information:\n{echo_addresses}\n======{shutdowns}",
        reply_markup=ReplyKeyboardRemove(),
    )


async def _fetch_addresses(state: FSMContext) -> str:
    data = await state.get_data()
    echo_addresses = ""
    if addresses := data.get("addresses") or []:
        echo_addresses = "\nYour Addresses:\n - "
        echo_addresses += "\n - ".join(addresses)

    return echo_addresses


async def _fetch_shutdowns(state: FSMContext) -> str:
    data = await state.get_data()
    addresses = data.get("addresses")
    if not addresses:
        return ""

    shutdowns = "\nFuture ShutDowns:\n - "
    for address in addresses:
        shutdowns += f"\n - [{address}] 20.07 (10:00 - 14:00)"

    return shutdowns


async def main() -> None:
    """
    Initialize Bot instance with default bot properties which will be passed to all API calls
    """
    bot = Bot(token=TG_BOT_API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(form_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
