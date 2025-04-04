from datetime import datetime

from sqlalchemy import ForeignKey, DateTime
from sqlalchemy import String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship

from src.config.constants import SupportedCity
from src.utils import utcnow


class BaseModel(AsyncAttrs, DeclarativeBase):
    id: Mapped[int]


class User(BaseModel):
    """User model representing a Telegram user in the system."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    chat_id: Mapped[int]

    # Relationships
    addresses: Mapped[list["UserAddress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["UserNotification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return f"User #{self.id} {self.name} "

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, name={self.name!r})"

    async def get_addresses(self, city: SupportedCity | None = None) -> list["UserAddress"]:
        addresses: list[UserAddress] = await self.awaitable_attrs.addresses
        if city is not None:
            addresses = [address for address in addresses]

        return addresses


class UserAddress(BaseModel):
    """User address model representing a Telegram user in the system."""

    __tablename__ = "user_addresses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    city: Mapped[str]
    address: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="addresses")

    def __repr__(self) -> str:
        return (
            f"Address("
            f"id={self.id!r}, "
            f"city={self.city!r}, "
            f"user_id={self.user_id!r}, "
            f"address={self.address!r}"
            f")"
        )


class UserNotification(BaseModel):
    """Model for tracking user notifications about utility services."""

    __tablename__ = "user_notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    hash: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="notifications")

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return f"UserNotification(id={self.id}, user_id={self.user_id}, at={self.created_at})"
