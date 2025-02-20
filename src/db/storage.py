"""
Storage implementation for managing Telegram bot user data with JSON file persistence.
"""

import json
import logging
import dataclasses
from collections import defaultdict
from typing import Any, DefaultDict

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
        self.storage: dict[int, UserDataRecord] = self._load_from_file()
        self.state: DefaultDict[StorageKey, StateType] = defaultdict(None)

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        """Set state for specified key."""
        self.state[key] = state

    async def get_state(self, key: StorageKey) -> StateType | None:
        """Retrieve state for specified key."""
        return self.state.get(key)

    async def set_data(self, key: StorageKey, data: dict[str, Any]) -> None:
        """Save user data and persist to storage."""
        # async with session_scope() as session:

        if not (user_data := self.storage.get(key.user_id)):
            user_data = UserDataRecord(id=key.user_id)

        user_data.data = data
        self.storage[key.user_id] = user_data
        self._save_to_file()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        """Retrieve user data for specified key."""
        with UserRepository() as repo:
            user = await repo.get(key.user_id)

        if user is None:
            return {}

        return user.data

    async def close(self) -> None:
        """Clean up resources if needed."""

    def _save_to_file(self) -> None:
        """Temp method for saving user's address (will be placed to use SQLite instead"""
        if not self.data_file_path.exists():
            self.data_file_path.touch()

        with open(self.data_file_path, "wt", encoding="utf-8") as f:
            data = {
                user_id: data_record.dump()
                for user_id, data_record in self.storage.items()
            }
            json.dump(data, f)

    def _load_from_file(self) -> dict[int, UserDataRecord]:
        """Temp method for saving user's address (will be placed to use SQLite instead"""
        data = {}
        if self.data_file_path.exists():
            try:
                with open(self.data_file_path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.exception("Couldn't read from storage file: %r", exc)

        return {
            int(user_id): UserDataRecord.load(user_data)
            for user_id, user_data in data.items()
        }
