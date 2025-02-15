import abc
from typing import Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.db.models import User
from src.db.session import make_sa_session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository interface.
    """

    def __init__(self):
        self.session: AsyncSession | None = None

    def __enter__(self) -> "BaseRepository[T]":
        self.session = make_sa_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session = None

    @abc.abstractmethod
    async def get(self, id_: int) -> T:
        pass

    @abc.abstractmethod
    async def save(self, value: T) -> None:
        pass

    @abc.abstractmethod
    async def delete(self, item: T) -> None:
        pass


class UserRepository(BaseRepository[User]):
    async def get(self, id_: int) -> T:
        statement = select(User).where(User.id == id_)
        user = await self.session.execute(statement)
