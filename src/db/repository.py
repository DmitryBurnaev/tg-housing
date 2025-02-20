import hashlib
import json
import logging
from types import TracebackType
from typing import Generic, TypeVar, Any, Unpack, Self

from mypy.build import TypedDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.config.app import SupportedCity
from src.db.models import User, UserNotification, UserAddress
from src.db.session import make_sa_session
from src.utils import ParsedAddress

T = TypeVar("T")
logger = logging.getLogger(__name__)


class UserData(TypedDict):
    id: int
    first_name: str
    last_name: str


class BaseRepository(Generic[T]):
    """
    Base repository interface.
    """

    model: type[T]

    def __init__(self, auto_commit: bool = True, auto_flush: bool = True) -> None:
        self.session: AsyncSession | None = None
        self.auto_flush: bool = auto_flush
        self.auto_commit: bool = auto_commit

    def __enter__(self) -> Self:
        self.session = make_sa_session()
        return self

    def __exit__(
        self,
        exc_type: type[Exception],
        exc_val: Exception,
        exc_tb: TracebackType | None,
    ) -> None:
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
        statement = select(self.model).where(self.model.id == id_)
        return await self.session.execute(statement)

    async def create(self, value: dict[str, Any]) -> T:
        """Creates new instance"""
        instance = self.model(**value)
        self.session.add(instance)
        await self.flush_and_commit()
        return instance

    async def update(self, instance: T, **value: dict[str, Any]) -> None:
        """Just updates instance with provided update_value."""
        for key, value in value.items():
            setattr(instance, key, value)

        self.session.add(instance)
        await self.flush_and_commit()

    async def delete(self, instance: T) -> None:
        """Remove the instance from the DB."""
        await self.session.delete(instance)
        await self.flush_and_commit()


class UserRepository(BaseRepository[User]):
    """User's repository."""

    model = User

    async def get_or_create(self, id_: int, **user_data: Unpack[UserData]) -> User:
        user = await self.get(id_)
        if user is None:
            user = await self.create(value=user_data)
        return user

    async def get_addresses(self, user_id: int) -> list[UserAddress]:
        """Returns list of user's addresses"""
        user: User = await self.get(user_id)
        return user.addresses

    async def add_address(
        self,
        user_id: int,
        city: SupportedCity,
        address: ParsedAddress,
    ) -> UserAddress:
        """
        Adds new address to database.
        Args:
            user_id: current user id
            city: selected city
            address: user address (got from user's input)
        Returns:
            address: new user address
        """
        user: User = await self.get(user_id)
        user_address: UserAddress = UserAddress(
            user_id=user_id,
            address=str(address),
            city=city,
        )
        user.addresses.append(user_address)
        await self.flush_and_commit()
        return user_address

    async def get_notifications(self, user_id: int) -> list[UserNotification]:
        """Returns list of user's notifications"""
        user = await self.get(user_id)
        return user.notifications

    async def has_notification(
        self,
        user_id: int,
        notification_data: dict[str, Any],
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
