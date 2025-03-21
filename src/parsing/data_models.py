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
        return all(
            [
                self.city == other.city,
                self.street_name == other.street_name,
                self.street_prefix == other.street_prefix,
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

    def __gt__(self, other: datetime.datetime) -> bool:  # type: ignore[override]
        if DEBUG_SHUTDOWNS:
            logger.debug("Fake data comparator: %r > %r | always True", self, other)
            return True

        if self.end is None:
            logger.debug("Fake data comparator: %r > %r | always False", self, other)
            return False

        if isinstance(self.end, datetime.date):
            return self.end > other

        return self.end.astimezone(datetime.timezone.utc) >= other

    def __lt__(self, other: datetime.datetime) -> bool:  # type: ignore[override]
        if self.end is None:
            logger.debug("Fake data comparator: %r < %r | always True", self, other)
            return True

        if isinstance(self.end, datetime.date):
            return self.end < other

        return self.end.astimezone(datetime.timezone.utc) < other

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
