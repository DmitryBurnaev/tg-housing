from datetime import datetime
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class BaseModel(DeclarativeBase):
    id: Mapped[int] = mapped_column(primary_key=True)
    pass


class User(BaseModel):
    """User model representing a Telegram user in the system."""

    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(30))
    fullname: Mapped[Optional[str]]

    # relations
    addresses: Mapped[list["UserAddress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["UserNotification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"


class UserAddress(BaseModel):
    """User address model representing a Telegram user in the system."""

    __tablename__ = "user_addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    city: Mapped[str]
    address: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # relations
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


class UserNotification(BaseModel, table=True):
    """Model for tracking user notifications about utility services."""

    __tablename__ = "user_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    address_id: Mapped[int] = mapped_column(ForeignKey("user_addresses.id"))
    notification_type: Mapped[str]
    notification_hash: Mapped[str]
    notified_at: Mapped[datetime]

    # Relationships
    user: Mapped["User"] = relationship(back_populates="notifications")
    address: Mapped["UserAddress"] = relationship(back_populates="notifications")

    def __str__(self) -> str:
        return f"UserNotification(type={self.notification_type}, at={self.notified_at})"

    def __repr__(self) -> str:
        return (
            f"UserNotification(id={self.id}, user_id={self.user_id}, "
            f"address_id={self.address_id}, type={self.notification_type}, "
            f"at={self.notified_at})"
        )
