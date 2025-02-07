from datetime import datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    tg_id: int = Field()
    username: str


class UserAddress(SQLModel, table=True):
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    address: str
    city: str


class UserNotification(SQLModel, table=True):
    id: int = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    address_id: int = Field(foreign_key="address.id")
    notification_type: str
    notified_at: datetime
