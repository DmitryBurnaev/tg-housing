from typing import List
from typing import Optional
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class BaseModel(DeclarativeBase):
    pass


class User(BaseModel):
    """User model representing a Telegram user in the system."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    fullname: Mapped[Optional[str]]

    # relations
    addresses: Mapped[List["Address"]] = relationship(
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
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))

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
