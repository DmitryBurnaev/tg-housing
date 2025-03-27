"""
Storage implementation for managing Telegram bot user data with JSON file persistence.
"""

import logging
from collections import defaultdict
from typing import Any, DefaultDict, Dict

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType
from aiogram.types import User as TelegramUser

from src.config.constants import SupportedCity
from src.db.repository import UserRepository

logger = logging.getLogger(__name__)


class UserStorage(BaseStorage):
    """
    Wrapper around Telegram bot user data storage class,
    which allows to store user data to the DB (PostgreSQL).

    Implements the aiogram BaseStorage interface while providing DB persistence
    for user data and state management.
    """

    def __init__(self) -> None:
        self.memory_storage: DefaultDict[StorageKey, str | None] = defaultdict(None)
        self.repository: UserRepository = UserRepository()

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        """Set state for specified key."""
        self.memory_storage[key] = state.state if isinstance(state, State) else state

    async def get_state(self, key: StorageKey) -> str | None:
        """Retrieve state for specified key."""
        return self.memory_storage.get(key)

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        """Just requires from abstract base class"""
        pass

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        """Retrieve user data for specified key."""
        user = await self.repository.first(key.user_id)
        if user is None:
            return {}

        addresses: list[str] = [
            user_address.address for user_address in (await user.awaitable_attrs.addresses)
        ]
        return {
            "id": user.id,
            "chat_id": user.chat_id,
            "addresses": addresses,
        }

    async def update_data(self, key: StorageKey, data: dict[str, Any]) -> dict[str, Any]:
        """
        Update users data (and related items like addresses) for specified key.
        """
        tg_user: TelegramUser | None = data.get("user")
        if not tg_user:
            logger.warning("User[%s] data not found for key %s. Skip updating!", key.user_id, key)
            return data

        city: SupportedCity | None = data.get("city")
        new_addresses: list[str] = data.get("new_addresses") or []
        rm_addresses: list[str] = data.get("rm_addresses") or []
        if not new_addresses and not rm_addresses:
            logger.warning(
                "User[%s] unable to update data (no new or rm address provided)!", key.user_id
            )
            return data

        user = await self.repository.get_or_create(
            tg_user.id,
            value={"name": tg_user.full_name, "chat_id": key.chat_id},
        )
        if new_addresses:
            logger.info("User[%s] adding a new addresses: %s", user.id, new_addresses)
            await self.repository.add_addresses(user, city=city, new_addresses=new_addresses)

        if rm_addresses:
            logger.info("User[%s] removing addresses: %s", user.id, new_addresses)
            await self.repository.remove_addresses(user, addresses=rm_addresses)

        return data

    async def close(self) -> None:
        """Cleanup client resources and disconnect from MongoDB."""
        await self.repository.close()
