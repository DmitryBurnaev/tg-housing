from typing import Sequence

from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.utils.formatting import as_marked_section, as_key_value, Text, as_list

from src.i18n import _
from src.config.app import SupportedService
from src.providers.shutdowns import ShutDownProvider, ShutDownByServiceInfo

DT_FORMAT = "%d.%m.%Y %H:%M"
SERVICE_NAME_MAP = {
    SupportedService.ELECTRICITY: _("💡 Electricity"),
    SupportedService.COLD_WATER: _("︎🚰 Cold Water"),
    SupportedService.HOT_WATER: _("🚿 Hot Water"),
}


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


async def fetch_addresses(state: FSMContext) -> Text | str:
    """
    If addresses exist, it returns a marked section that displays the addresses,
    otherwise it returns the string "No address yet :(".

    Args:
        state: The state of the FSMContext.

    """
    if addresses := await get_addresses(state):
        return as_marked_section(_("Your Addresses:"), *addresses, marker="☑︎ ")

    return _("No address yet :(")


async def fetch_shutdowns(state: FSMContext) -> Sequence[Text | str]:
    if not (addresses := await get_addresses(state)):
        return [_("No address yet :(")]

    shutdowns_by_service: list[ShutDownByServiceInfo] = ShutDownProvider.for_addresses(addresses)
    if not shutdowns_by_service:
        return [_("No shutdowns :)")]

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
                    as_key_value(_("Start"), shutdown_info.start_repr),
                    as_key_value(_("End"), shutdown_info.end_repr),
                    marker="   - ",
                )
            )
        result.append(
            as_marked_section(
                title,
                *values,
                marker=" ⚠︎ ",
            )
        )

    return result


async def get_addresses(state: FSMContext) -> list[str]:
    data = await state.get_data()
    return data.get("addresses") or []


async def answer(
    message: Message,
    title: str,
    entities: Sequence[str | Text] | None = None,
    reply_keyboard: bool = False,
) -> None:
    """Sends answer with provided message, title and additional entities."""
    entities = entities or []
    content = as_list(title, *entities, sep="\n\n")
    reply_markup = ReplyKeyboardRemove() if reply_keyboard else None

    await message.answer(
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup,
        **content.as_kwargs(replace_parse_mode=False),
    )
