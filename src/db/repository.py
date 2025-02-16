import hashlib
import json
import logging
from typing import Generic, TypeVar, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.db.models import User, UserNotification
from src.db.session import make_sa_session

T = TypeVar("T")
logger = logging.getLogger(__name__)


class BaseRepository(Generic[T]):
    """
    Base repository interface.
    """

    def __init__(self, auto_commit: bool = True, auto_flush: bool = True) -> None:
        self.session: AsyncSession | None = None
        self.auto_flush: bool = auto_flush
        self.auto_commit: bool = auto_commit

    def __enter__(self) -> "BaseRepository[T]":
        self.session = make_sa_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session = None

    async def flush_and_commit(self) -> None:
        """Sending changes to database."""
        if self.auto_flush:
            assert self.session.flush()

        if not self.auto_commit:
            logger.debug("Skipping commit")
            return

        try:
            logger.debug("Committing changes")
            await self.session.commit()
        except Exception as exc:
            logger.error("Failed to commit changes", exc_info=exc)
            await self.session.rollback()
            raise exc

    async def get(self, id_: int) -> T:
        """Selects instance by provided ID"""
        statement = select(T).where(T.id == id_)
        return await self.session.execute(statement)

    async def update(self, instance: T, **update_value: dict[str, Any]) -> None:
        """Just updates instance with provided update_value."""
        for key, value in update_value.items():
            setattr(instance, key, value)

        self.session.add(instance)
        await self.flush_and_commit()

    async def delete(self, instance: T) -> None:
        """Remove the instance from the DB."""
        await self.session.delete(instance)
        await self.flush_and_commit()


class UserRepository(BaseRepository[User]):
    """User's repository."""

    async def get_notifications(self, user_id: int) -> list[UserNotification]:
        user = await self.get(user_id)
        return user.notifications

    async def has_notification(
        self, user_id: int, notification_data: dict[str, Any]
    ) -> bool:
        """Searching already sent notifications by provided notification data."""
        user = await self.get(user_id)
        notification_hash = hashlib.sha256(
            json.dumps(notification_data).encode()
        ).hexdigest()
        statement = select(UserNotification).where(
            UserNotification.user_id == user.id,
            UserNotification.notification_hash == notification_hash,
        )
        return (await self.session.execute(statement)).scalar() is not None
