"""DB-specific module which provide specific operations on database."""

import hashlib
import json
import logging
from functools import wraps
from types import TracebackType
from typing import (
    Generic,
    TypeVar,
    Any,
    Self,
    TypedDict,
    Sequence,
    Unpack,
    Callable,
    Awaitable,
    ParamSpec,
)

from sqlalchemy import select, BinaryExpression, insert, delete
from sqlalchemy.exc import NoResultFound, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.decorators import decohints
from src.config.constants import SupportedCity
from src.db.models import BaseModel, User, UserNotification, UserAddress
from src.db.session import make_sa_session

ModelT = TypeVar("ModelT", bound=BaseModel)
logger = logging.getLogger(__name__)
P = ParamSpec("P")
RT = TypeVar("RT")


@decohints
def transaction_commit(func: Callable[P, Awaitable[RT]]) -> Callable[P, Awaitable[RT]]:
    """Commits changes to the DB and rollback if something went wrong."""

    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> RT:
        self = args[0]
        if not isinstance(self, BaseRepository):
            raise TypeError("First argument must be BaseRepository instance")

        func_details: str = f"[{self.model.__name__}]: {func.__name__}({args}, {kwargs})"
        try:
            logger.debug("[DB] Entering transaction block %s", func_details)

            result = await func(*args, **kwargs)
            if self.auto_flush:
                await self.session.flush()

            async with self.session.begin_nested():
                logger.debug("[DB] Commiting %s", func_details)
                await self.session.commit()

            return result

        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("[DB] Error during operation %s: %r", func_details, exc)
            raise exc

    return wrapper


class UsersFilter(TypedDict):
    """Simple structure to filter users by specific params"""

    ids: list[int] | None


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
        statement = select(self.model).filter_by(id=instance_id)
        result = await self.session.execute(statement)
        row: Sequence[ModelT] | None = result.fetchone()
        if not row:
            return None

        return row[0]

    async def all(self, **filters: int | str | list[int] | None) -> list[ModelT]:
        """Selects instances from DB"""
        filters_stmts: list[BinaryExpression[bool]] = []
        if (ids := filters.pop("ids", None)) and isinstance(ids, list):
            filters_stmts.append(self.model.id.in_(ids))

        statement = select(self.model).filter_by(**filters)
        if filters_stmts:
            statement = statement.filter(*filters_stmts)

        result = await self.session.execute(statement)
        return [row[0] for row in result.fetchall()]

    @transaction_commit
    async def create(self, value: dict[str, Any]) -> ModelT:
        """Creates new instance"""
        logger.debug("[DB] Creating [%s]: %s", self.model.__name__, value)
        instance = self.model(**value)
        self.session.add(instance)
        return instance

    async def get_or_create(self, id_: int, value: dict[str, Any]) -> ModelT:
        """Tries to find instance by ID and create if it wasn't found"""
        instance = await self.first(id_)
        if instance is None:
            instance = await self.create(value | {"id": id_})

        return instance

    @transaction_commit
    async def update(self, instance: ModelT, **value: dict[str, Any]) -> None:
        """Just updates instance with provided update_value."""
        for key, value in value.items():
            setattr(instance, key, value)

        self.session.add(instance)

    @transaction_commit
    async def delete(self, instance: ModelT) -> None:
        """Remove the instance from the DB."""
        await self.session.delete(instance)

    @transaction_commit
    async def delete_by_ids(self, removing_ids: Sequence[int]) -> None:
        """Remove the instances from the DB."""
        statement = delete(self.model).filter(self.model.id.in_(removing_ids))
        await self.session.execute(statement)


class UserRepository(BaseRepository[User]):
    """User's repository."""

    model = User

    async def filter(self, **filters: Unpack[UsersFilter]) -> list[User]:
        """Extra filtering users by some parameters."""
        return await self.all(**filters)

    async def get_addresses(
        self,
        user_id: int,
        city: SupportedCity | None = None,
    ) -> list[UserAddress]:
        """
        Returns list of user's addresses
        """
        user: User = await self.get(user_id)
        addresses = await user.get_addresses(city)
        return addresses

    async def get_addresses_plain(
        self, user_id: int, city: SupportedCity | None = None
    ) -> list[str]:
        """Returns list of user's addresses"""
        user: User = await self.get(user_id)
        return [user_address.address for user_address in (await user.get_addresses(city))]

    @transaction_commit
    async def add_addresses(
        self, user: User, city: SupportedCity, new_addresses: list[str]
    ) -> None:
        """Finds missing addresses and insert this ones"""
        user_addresses = await self.get_addresses(user.id)
        stored_addresses = set(user_address.address for user_address in user_addresses)
        missing_addresses = {str(addr) for addr in new_addresses} - stored_addresses
        if missing_addresses:
            logger.debug(
                "[DB] Updating addresses for user [%s]: added new addresses: %s",
                user.id,
                missing_addresses,
            )
            for address in missing_addresses:
                await self.add_address(user, city=city, address=address)
        else:
            logger.debug("[DB] No new addresses updated for user [%s]", user.id)

    @transaction_commit
    async def remove_addresses(self, user: User, addresses: list[str]) -> None:
        """Finds missing addresses and insert this ones"""
        stored_addresses = {
            user_address.address: user_address.id
            for user_address in await self.get_addresses(user.id)
        }
        removing_ids = [
            stored_addresses.get(address) for address in addresses if address in stored_addresses
        ]
        if not removing_ids:
            logger.debug("[DB] No addresses deleted for user [%s] (no stored ones)", user.id)
            return

        logger.info(
            "[DB] Deleting addresses for user [%s] addresses: %s | ids: %s",
            user.id,
            addresses,
            removing_ids,
        )
        statement = delete(UserAddress).filter(UserAddress.id.in_(removing_ids))
        await self.session.execute(statement)

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
        await self.session.flush([user_address])
        return user_address

    async def get_notifications(self, user_id: int) -> list[UserNotification]:
        """Returns list of user's notifications"""
        user = await self.get(user_id)
        return user.notifications

    async def has_notification(self, user_id: int, notification_data: str) -> bool:
        """Searching already sent notifications by provided notification data."""
        user = await self.get(user_id)
        notification_hash = hashlib.sha256(notification_data.encode()).hexdigest()

        statement = select(UserNotification).where(
            UserNotification.user_id == user.id,
            UserNotification.hash == notification_hash,
        )
        return (await self.session.execute(statement)).scalar() is not None

    @transaction_commit
    async def add_notification(self, user_id: int, notification_data: str) -> None:
        """Adding fact about sending notification to the database"""
        user = await self.get(user_id)
        logger.info("[DB] Adding notification for user [%s]", user)
        notification_hash = hashlib.sha256(notification_data.encode()).hexdigest()
        notification = UserNotification(user_id=user.id, hash=notification_hash)
        self.session.add(notification)
        await self.session.flush([notification])
