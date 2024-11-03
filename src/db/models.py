import dataclasses
import datetime
import uuid
from re import Pattern
from typing import NamedTuple

from src.config.app import SupportedCity
from src.utils import get_street_and_house, ADDRESS_DEFAULT_PATTERN


class Address(NamedTuple):
    """Structural form of storing some user's address"""

    city: SupportedCity
    street: str
    house: int | None
    raw: str

    def matches(self, other: "Address") -> bool:
        """
        Check if the given Address object matches with the current Address object.

        Parameters:
        - other (Address): The Address object to compare with.

        Returns:
            - bool: True if all attributes (city, street, house) of both Address objects match,
                    False otherwise.
        """
        return all(
            [
                self.city == other.city,
                self.street == other.street,
                self.house == other.house,
            ]
        )

    @classmethod
    def from_string(cls, raw_address: str, pattern: Pattern[str] | None = None) -> "Address":
        pattern = pattern or ADDRESS_DEFAULT_PATTERN
        street_name, houses = get_street_and_house(
            pattern=pattern,
            address=raw_address,
        )

        return cls(
            city=SupportedCity.SPB,
            street=street_name,
            house=houses[0] if houses else None,
            raw=raw_address,
        )


class DateRange(NamedTuple):
    start: datetime.datetime
    end: datetime.datetime

    def __gt__(self, other: datetime.datetime) -> bool:
        return self.end.astimezone(datetime.timezone.utc) > other

    def __lt__(self, other: datetime.datetime) -> bool:
        return self.end.astimezone(datetime.timezone.utc) < other

    def __str__(self) -> str:
        return f"{self.start.isoformat()} - {self.end.isoformat()}"


@dataclasses.dataclass
class User:
    id: uuid.UUID
    name: str
    city: SupportedCity
    raw_address: str
    address: Address | None = None

    def __post_init__(self):
        street, houses = get_street_and_house(self.raw_address)
        house = houses[0] if houses else None
        self.address = Address(city=self.city, street=street, house=house, raw=self.raw_address)

    def echo_results(self, date_ranges: dict[Address, set[DateRange]]) -> None:
        print(f"[{self.name}] === {self.address.raw} ===")
        now_time = datetime.datetime.now(datetime.timezone.utc)
        for address, date_ranges in date_ranges.items():
            actual_ranges = []
            for date_range in date_ranges:
                if date_range > now_time:
                    actual_ranges.append(date_range)

            if actual_ranges:
                print(f" - {address}")
                print(f"   - {'\n   - '.join(map(str, actual_ranges))}")
