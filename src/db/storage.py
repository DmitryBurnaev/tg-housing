"""
Storage implementation for managing Telegram bot user data with JSON file persistence.
"""

import logging
from collections import defaultdict
from typing import Any, DefaultDict, Dict

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType
from aiogram.types import User as TelegramUser

from src.config.app import SupportedCity, TMP_DATA_DIR
from src.db.models import User
from src.db.repository import UserRepository

logger = logging.getLogger(__name__)


class UserStorage(BaseStorage):
    """
    Wrapper around Telegram bot user data storage class,
    which allows to store user data to the DB (PostgreSQL).

    Implements the aiogram BaseStorage interface while providing DB persistence
    for user data and state management.
    """

    data_file_path = TMP_DATA_DIR / "user_address.json"

    def __init__(self) -> None:
        self.storage: DefaultDict[StorageKey, str | None] = defaultdict(None)

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        """Set state for specified key."""
        self.storage[key] = state.state if isinstance(state, State) else state

    async def get_state(self, key: StorageKey) -> str | None:
        """Retrieve state for specified key."""
        return self.storage[key]

    async def set_data(self, key: StorageKey, data: Dict[str, Any]) -> None:
        """Just requires from abstract base class"""
        pass

    async def update_data(self, key: StorageKey, data: dict[str, Any]) -> dict[str, Any]:
        """
        Update users data (and related items like addresses) for specified key.
        """
        tg_user: TelegramUser | None = data.get("user")
        if not tg_user:
            raise ValueError("User data not found.")

        city: SupportedCity | None = data.get("city")
        address: str | None = data.get("address")
        if not city or not address:
            raise ValueError("Address data not found.")

        async with UserRepository() as user_repo:
            user = await user_repo.get_or_create(
                tg_user.id,
                value={"name": tg_user.full_name, "chat_id": key.chat_id},
            )
            await user_repo.update_addresses(user, city=city, new_addresses=[address])

        return data

    @staticmethod
    async def _get_or_create_user(
        repo: UserRepository, tg_user: TelegramUser, key: StorageKey
    ) -> User:
        user = await repo.get_or_create(
            tg_user.id, value={"name": tg_user.full_name, "chat_id": key.chat_id}
        )
        return user

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        """Retrieve user data for specified key."""
        async with UserRepository() as repo:
            user = await repo.get(key.user_id)

        if user is None:
            return {}

        return {
            "chat_id": user.chat_id,
            "addresses": user.addresses,
        }

    async def close(self) -> None:
        """Clean up resources if needed."""
