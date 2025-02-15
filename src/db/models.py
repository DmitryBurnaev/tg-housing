"""
SQLModel-based database models for the Telegram bot application.

Defines the data models for users, addresses, and notifications.
"""

from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship


class User(SQLModel, table=True):
    """User model representing a Telegram user in the system."""

    __tablename__ = "users"

    id: int = Field(primary_key=True)
    tg_id: int = Field()
    username: str
    data: dict = Field()

    # Relationships
    addresses: list["UserAddress"] = Relationship(back_populates="user")
    notifications: list["UserNotification"] = Relationship(back_populates="user")

    def __str__(self) -> str:
        return f"User(id={self.id}, username={self.username})"

    def __repr__(self) -> str:
        return f"User(id={self.id}, tg_id={self.tg_id}, " f"username={self.username})"


class UserAddress(SQLModel, table=True):
    """Model for storing user addresses and their associated cities."""

    __tablename__ = "user_addresses"

    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    address: str
    city: str

    # Relationships
    user: User = Relationship(back_populates="addresses")
    notifications: list["UserNotification"] = Relationship(back_populates="address")

    def __str__(self) -> str:
        return f"UserAddress(address={self.address}, city={self.city})"

    def __repr__(self) -> str:
        return (
            f"UserAddress(id={self.id}, user_id={self.user_id}, "
            f"address={self.address}, city={self.city})"
        )


class UserNotification(SQLModel, table=True):
    """Model for tracking user notifications about utility services."""

    __tablename__ = "user_notifications"

    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    address_id: int = Field(foreign_key="user_addresses.id")
    notification_type: str
    notified_at: datetime

    # Relationships
    user: User = Relationship(back_populates="notifications")
    address: UserAddress = Relationship(back_populates="notifications")

    def __str__(self) -> str:
        return f"UserNotification(type={self.notification_type}, at={self.notified_at})"

    def __repr__(self) -> str:
        return (
            f"UserNotification(id={self.id}, user_id={self.user_id}, "
            f"address_id={self.address_id}, type={self.notification_type}, "
            f"at={self.notified_at})"
        )
