"""
Storage implementation for managing Telegram bot user data with JSON file persistence.
"""

import logging
import dataclasses
from collections import defaultdict
from typing import Any, DefaultDict

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType

from src.config.app import TMP_DATA_DIR
from src.db.repository import UserRepository

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class UserDataRecord:
    """Data structure for storing user-specific data with serialization capabilities."""

    id: int
    data: dict[str, Any] = dataclasses.field(default_factory=dict)

    def dump(self) -> dict:
        """Serialize the user data record to a dictionary."""
        return dataclasses.asdict(self)

    @classmethod
    def load(cls, data: dict) -> "UserDataRecord":
        """Create a UserDataRecord instance from a dictionary."""
        return cls(**data)


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

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        """Save user data and persist to storage."""

        async with UserRepository() as user_repo:
            user = await user_repo.get_or_create(
                id_=key.user_id,
                value={
                    "chat_id": key.chat_id,
                },
            )
            city = data.get("city")
            address = data.get("address")
            if city and address:
                await user_repo.update_addresses(user, city=city, new_addresses=address)

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
