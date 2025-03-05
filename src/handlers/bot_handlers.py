"""
This module defines a Telegram bot using the aiogram library to manage user addresses
in a conversation flow. The bot uses FSMContext to manage the state of the conversation
and provides a structured way for users to interact with address-related commands.
"""

import logging

from aiogram import F, Router
from aiogram.utils import markdown
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    ReplyKeyboardRemove,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from src.config.app import SupportedCity
from src.i18n import _
from src.handlers.helpers import (
    UserAddressStatesGroup,
    fetch_addresses,
    get_addresses,
    fetch_shutdowns,
    answer,
)
from src.utils import parse_address, ParsedAddress

form_router = Router()


@form_router.message(Command("address"))
async def command_address(message: Message, state: FSMContext) -> None:
    """
    Transition to state "set_address"
    """
    await state.set_state(UserAddressStatesGroup.address)
    await message.answer(
        _("What do you want?"),
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=_("Add Address")),
                    KeyboardButton(text=_("Remove Address")),
                ]
            ],
            resize_keyboard=True,
        ),
    )


@form_router.message(UserAddressStatesGroup.address, F.text.casefold() == _("Add Address").lower())
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
        _("Ok, Sent me your address (without city, default - SPB)"),
        reply_markup=ReplyKeyboardRemove(),
    )


@form_router.message(
    UserAddressStatesGroup.address, F.text.casefold() == _("Remove Address").lower()
)
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
        _("What address do you want to remove?"),
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=address)
                    for address in state_data.get("addresses", None) or []
                ]
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
    if not message.from_user:
        await answer(message, _("Sorry, you are not authorized to do that."))
        return

    if not message.text:
        await answer(message, _("Please enter a new address."))
        return

    new_address: ParsedAddress = parse_address(message.text)
    if not new_address.completed:
        await state.set_state(UserAddressStatesGroup.add_address)
        await answer(
            message,
            title=_('Ups... we can\'t parse address "{message_text} (got {new_address})".').format(
                message_text=message.text,
                new_address=str(new_address),
            ),
            reply_keyboard=True,
        )
        return

    if new_address:
        await state.update_data(
            user=message.from_user,
            city=SupportedCity.SPB,
            addres=new_address,
        )
        await state.set_state(state=None)

    await answer(
        message,
        title=_('Ok, I\'ll remember your new address "{new_address}".').format(
            new_address=new_address
        ),
        entities=[await fetch_addresses(state)],
        reply_keyboard=True,
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
    new_addresses: list[str] = [
        address for address in await get_addresses(state) if address != message.text
    ]
    await state.update_data({"addresses": new_addresses})
    await state.set_state(state=None)

    await answer(
        message,
        title=_('OK. Address "{message.text}" was removed!').format(message=message),
        entities=[await fetch_addresses(state)],
        reply_keyboard=True,
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
    await message.answer(_("Cancelled."), reply_markup=ReplyKeyboardRemove())


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
    if not message.from_user:
        await answer(message, _("Sorry, you are not authorized to do that."))
        return

    await answer(
        message,
        title=_("Hi, {full_name}!").format(full_name=markdown.bold(message.from_user.full_name)),
        entities=[await fetch_addresses(state)],
        reply_keyboard=True,
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
    if not message.from_user:
        await answer(message, _("Sorry, you are not authorized to do that."))
        return

    await state.clear()
    await answer(
        message,
        title=_("Ok, I forgot all for you, {full_name}!").format(
            full_name=markdown.bold(message.from_user.full_name)
        ),
        reply_keyboard=True,
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
    addresses = await fetch_addresses(state)
    shutdowns = await fetch_shutdowns(state)
    await answer(message, title=_("Ok, That's your information:"), entities=[addresses, *shutdowns])
