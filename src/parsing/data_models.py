import dataclasses
import datetime
import uuid
import logging
from re import Pattern
from typing import NamedTuple

from src.config.app import DEBUG_SHUTDOWNS
from src.config.constants import SupportedCity
from src.utils import parse_address, ADDRESS_DEFAULT_PATTERN

logger = logging.getLogger(__name__)


class Address(NamedTuple):
    """
    Structural form of storing some user's address
    TODO: may be need to combine with ParsedAddress?
    """

    city: SupportedCity
    house: int | None
    raw: str
    street_name: str
    street_prefix: str = "ул"

    def __str__(self) -> str:
        return f"[{self.city}] {self.street_prefix}. {self.street_name}, {self.house}"

    def matches(self, other: "Address") -> bool:
        """
        Check if the given Address object matches with the current Address object.

        Parameters:
        - other (Address): The Address object to compare with.

        Returns:
            - bool: True if all attributes (city, street, house) of both Address objects match,
                    False otherwise.
        """
        logger.debug("Comparing Address: %s | %s", self, other)
        street_equal = (
            self.street_name.lower() in other.street_name.lower()
            and other.street_name.lower() in self.street_name.lower()
        )
        return all(
            [
                self.city == other.city,
                street_equal,
                self.house == other.house,
            ]
        )

    @classmethod
    def from_string(cls, raw_address: str, pattern: Pattern[str] | None = None) -> "Address":
        pattern = pattern or ADDRESS_DEFAULT_PATTERN
        parsed_address = parse_address(pattern=pattern, address=raw_address)
        return cls(
            city=SupportedCity.SPB,
            street_name=parsed_address.street_name,
            street_prefix=parsed_address.street_prefix,
            house=parsed_address.houses[0] if parsed_address.houses else None,
            raw=raw_address,
        )


class DateRange(NamedTuple):
    start: datetime.datetime | datetime.date | None
    end: datetime.datetime | datetime.date | None

    def __ge__(self, other: datetime.datetime) -> bool:  # type: ignore[override]
        """
        We need to return only date range after specific date (today)

        :param other: always utcnow (datetime)
        """
        if DEBUG_SHUTDOWNS:
            logger.warning("Fake data comparator: %r > %r | always True", self, other)
            return True

        if self.end is None:
            logger.warning("Unknown end time: %r > %r | always False", self, other)
            return False

        if isinstance(self.end, datetime.datetime):
            return self.end.astimezone(datetime.timezone.utc) >= other

        return self.end >= other.date()

    def __le__(self, other: datetime.datetime) -> bool:  # type: ignore[override]
        """
        In some cases we need to check that this range is before concrete date

        :param other: always utcnow (datetime)
        """
        if DEBUG_SHUTDOWNS:
            logger.warning("Fake data comparator: %r < %r | always True", self, other)
            return True

        if self.end is None:
            logger.warning("Unknown end time: %r < %r | always True", self, other)
            return True

        if isinstance(self.end, datetime.datetime):
            return self.end.astimezone(datetime.timezone.utc) <= other

        return self.end <= other.date()

    def __str__(self) -> str:
        start = self.start.isoformat() if self.start else None
        end = self.end.isoformat() if self.end else None
        return f"{start} - {end}"


@dataclasses.dataclass
class User:
    id: uuid.UUID
    name: str
    city: SupportedCity
    raw_address: str
    address: Address | None = None

    def __post_init__(self) -> None:
        parsed_address = parse_address(self.raw_address)
        self.address = Address(
            city=self.city,
            street_name=parsed_address.street_name,
            street_prefix=parsed_address.street_prefix,
            house=parsed_address.houses[0] if parsed_address.houses else None,
            raw=self.raw_address,
        )
