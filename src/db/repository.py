import hashlib
import json
import logging
from functools import wraps
from types import TracebackType
from typing import Generic, TypeVar, Any, Self, TypedDict, Sequence, Unpack, Callable, Awaitable

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.util import await_fallback

from src.config.app import SupportedCity
from src.db.models import BaseModel, User, UserNotification, UserAddress
from src.db.session import make_sa_session

ModelT = TypeVar("ModelT", bound=BaseModel)
logger = logging.getLogger(__name__)


def transaction_commit[RT, **P](func: Callable[P, Awaitable[RT]]) -> Callable[P, Awaitable[RT]]:
    """Commits changes to the DB and rollback if something went wrong."""

    @wraps(func)
    async def wrapper(self: "BaseRepository[ModelT]", *args: P.args, **kwargs: P.kwargs) -> RT:
        func_details: str = f"[{self.model.__name__}]: {func.__name__}({args}, {kwargs})"
        try:
            logger.debug("[DB] Entering transaction block %s", func_details)

            result = await func(self, *args, **kwargs)
            if self.auto_flush:
                await self.session.flush()

            async with self.session.begin():
                logger.debug("[DB] Commiting %s", func_details)
                await self.session.commit()

            return result

        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("[DB] Error during operation %s: %r", func_details, exc)
            raise exc

    return wrapper


def rollback_wrapper(func):
    @wraps(func)
    async def inner(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error(f"Error during DB operation: {exc}")
            raise exc

    return inner


class UsersFilter(TypedDict):
    city: SupportedCity


class BaseRepository(Generic[ModelT]):
    """
    Base repository interface.
    """

    model: type[ModelT]

    def __init__(
        self,
        session: AsyncSession | None = None,
        auto_commit: bool = True,
        auto_flush: bool = True,
    ) -> None:
        self.auto_flush: bool = auto_flush
        self.auto_commit: bool = auto_commit
        self.__session: AsyncSession | None = session

    async def __aenter__(self) -> Self:
        if not self.__session:
            self.__session = make_sa_session()
        return self

    async def __aexit__(
        self,
        exc_type: type[Exception],
        exc_val: Exception,
        exc_tb: TracebackType | None,
    ) -> None:
        if not self.__session:
            logger.debug("Session already closed")
            return

        await self.__session.close()
        self.__session = None

    async def close(self) -> None:
        """Closing current session"""
        if self.__session:
            logger.debug("Closing session")
            await self.__session.close()
            self.__session = None
        else:
            logger.debug("Session already closed")

    @property
    def session(self) -> AsyncSession:
        """Provide current session (open if it isn't created yet)"""
        if not self.__session:
            self.__session = make_sa_session()

        return self.__session

    async def flush_and_commit(self) -> None:
        """Sending changes to database."""
        if not self.session:
            raise RuntimeError("No active session")

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

    async def get(self, instance_id: int) -> ModelT:
        """Selects instance by provided ID"""
        instance: ModelT | None = await self.first(instance_id)
        if not instance:
            raise NoResultFound

        return instance

    async def first(self, instance_id: int) -> ModelT | None:
        """Selects instance by provided ID"""
        async with self.session.begin_nested() as session:
            statement = select(self.model).filter_by(id=instance_id)
            result = await self.session.execute(statement)
            row: Sequence[tuple[ModelT]] | None = result.fetchone()
            if not row:
                return None

            return row[0]

    async def all(self, **filters: str | int) -> list[ModelT]:
        """Selects instances from DB"""

        statement = select(self.model).filter_by(**filters)
        result = await self.session.execute(statement)
        return [row[0] for row in result.fetchall()]

    @rollback_wrapper
    async def create(self, value: dict[str, Any]) -> ModelT:
        """Creates new instance"""
        logger.debug(f"[DB] Creating [%s]: %s", self.model.__name__, value)
        async with self.session.begin_nested():
            instance = self.model(**value)
            self.session.add(instance)
            await self.flush_and_commit()

        return instance

    @rollback_wrapper
    async def get_or_create(self, id_: int, value: dict[str, Any]) -> ModelT:
        """Tries to find instance by ID and create if it wasn't found"""
        instance = await self.first(id_)
        if not instance:
            instance = await self.create(value | {"id": id_})

        return instance

    @rollback_wrapper
    async def update(self, instance: ModelT, **value: dict[str, Any]) -> None:
        """Just updates instance with provided update_value."""
        for key, value in value.items():
            setattr(instance, key, value)

        self.session.add(instance)
        await self.flush_and_commit()

    @rollback_wrapper
    async def delete(self, instance: ModelT) -> None:
        """Remove the instance from the DB."""
        await self.session.delete(instance)
        await self.flush_and_commit()


class UserRepository(BaseRepository[User]):
    """User's repository."""

    model = User

    async def filter(self, **filters: Unpack[UsersFilter]) -> list[User]:
        """Extra filtering users by some parameters."""
        return await self.all(**filters)

    async def get_addresses(self, user_id: int) -> list[UserAddress]:
        """
        Returns list of user's addresses
        """
        user: User = await self.get(user_id)
        return await user.get_addresses()

    async def get_addresses_list(self, user_id: int) -> list[str]:
        """Returns list of user's addresses"""
        user: User = await self.get(user_id)
        addresses = await user.get_addresses()
        return [user_address.address for user_address in addresses]

    async def update_addresses(
        self, user: User, city: SupportedCity, new_addresses: list[str]
    ) -> None:
        """Finds missing addresses and insert this ones"""
        user_addresses = await self.get_addresses(user.id)
        plain_addresses = set(user_address.address for user_address in user_addresses)
        missing_addresses = plain_addresses - {str(addr) for addr in new_addresses}
        for address in missing_addresses:
            await self.add_address(user, city=city, address=address)

    async def add_address(self, user: User, city: SupportedCity, address: str) -> UserAddress:
        """
        Adds new address to database.
        Args:
            city: chosen city (can be several for each user)
            user: current user
            address: user address (got from user's input)
        Returns:
            address: new user address
        """
        user_address: UserAddress = UserAddress(
            user_id=user.id,
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
        notification_hash = hashlib.sha256(json.dumps(notification_data).encode()).hexdigest()

        statement = select(UserNotification).where(
            UserNotification.user_id == user.id,
            UserNotification.notification_hash == notification_hash,
        )
        return (await self.session.execute(statement)).scalar() is not None
