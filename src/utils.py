import datetime
import re
import logging
from typing import NamedTuple

from src.config.app import MAPPING_STRING_REPLACEMENT

logger = logging.getLogger(__name__)
STREET_ELEMENTS_1 = r"\s+(?P<street_prefix>ал\.?|пл\.?)"

STREET_ELEMENTS = r"""\s+(?P<street_prefix>
ал\.?|
б-р\.?|
взв\.?|
взд\.?|
дор\.?|
ззд\.?|
км\.?|
к-цо\.?|
коса\.?|
лн\.?|
мгстр\.?|
наб\.?|
пер\.?|
пл\.?|
пр-д\.?|
пр-т\.?|пр-кт\.?|Пр-кт\.?|
пр-ка\.?|
пр-лок\.?|
пр\.?|
проул\.?|
рзд\.?|
ряд\.?|
с-р\.?|
с-к\.?|
сзд\.?|
тракт\.?|
туп\.?|
ул\.?|Ул\.?|
ш\.?)""".replace(
    "\n", ""
)

ADDRESS_DEFAULT_PATTERN = re.compile(
    r"^(?P<street_name>[А-Яа-яЁёA-Za-z\s]+?)(?:\s*,?\s*(?:д\.?|дом)?\s*(?P<start_house>\d+)(?:\s*[-–]\s*(?P<end_house>\d+))?(?:\s*корп\.\d+)?)?$"
)

REPLACE_STREET_PREFIX: dict[str, str] = {
    "пр": "пр-кт",
    "пр-т": "пр-кт",
}
DEFAULT_STREET_PREFIX = "ул"


class ParsedAddress(NamedTuple):
    street_prefix: str
    street_name: str
    houses: list[int]
    start_house: int | None = None
    end_house: int | None = None

    def __str__(self) -> str:
        houses = f", д. {','.join(map(str, self.houses))}" if self.houses else ""
        return f"{self.street_prefix}. {self.street_name}{houses}"

    @property
    def completed(self) -> bool:
        return all(
            [
                self.street_prefix,
                self.street_name,
                self.houses,
            ]
        )


def parse_address(address: str, pattern: re.Pattern[str] | None = None) -> ParsedAddress:
    """
    Searches street and house (or houses' range) from given string

    :param address: some string containing address with street and house (maybe range of houses)
    :param pattern: regexp's pattern for fetching street/houses from that
    :return <ParsedAddress> like ParsedAddress("пр-кт", "Наименование проспекта", [34, 35], 34, 35)
    """

    street_prefix = None
    if match := re.search(STREET_ELEMENTS, f" {address}"):
        street_prefix = match.group("street_prefix")
        address = (re.sub(STREET_ELEMENTS, "", f" {address}")).strip()

    if match := (pattern or ADDRESS_DEFAULT_PATTERN).search(address):
        street_name = match.group("street_name").strip()
        if street_prefix:
            street_prefix = street_prefix.strip().removesuffix(".").strip()
            street_prefix = REPLACE_STREET_PREFIX.get(street_prefix, street_prefix)
        else:
            street_prefix = MAPPING_STRING_REPLACEMENT.get(street_name, DEFAULT_STREET_PREFIX)
            logger.debug("Using default street prefix '%s'", street_prefix)

        start_house = int(match.group("start_house")) if match.group("start_house") else None
        if start_house:
            end_house = int(match.group("end_house")) if match.group("end_house") else start_house
            houses = list(range(start_house, end_house + 1))
        else:
            end_house = None
            houses = []

        parsed_address = ParsedAddress(
            street_prefix=street_prefix or "",
            street_name=street_name,
            houses=houses,
            start_house=start_house,
            end_house=end_house,
        )
    else:
        parsed_address = ParsedAddress(street_name=address, street_prefix="", houses=[])

    return parsed_address


def parse_street(address: str, pattern: re.Pattern[str]) -> ParsedAddress:
    """
    Searches street (and street-prefix) from given string

    :param address: some string containing address with street and prefix (like "пр-кт")
    :param pattern: regexp's pattern for fetching street/houses from that
    :return <ParsedAddress> like ParsedAddress("пр-кт", "Наименование проспекта", [])
    """
    if match := pattern.search(address):
        if street_prefix := match.group("street_prefix"):
            street_prefix = street_prefix.strip().removesuffix(".")
            street_prefix = REPLACE_STREET_PREFIX.get(street_prefix, street_prefix)

        street_name = match.group("street_name").strip()

        parsed_address = ParsedAddress(
            street_prefix=street_prefix or "",
            street_name=street_name,
            houses=[],
        )
    else:
        parsed_address = ParsedAddress(street_name=address, street_prefix="", houses=[])

    return parsed_address


def parse_street_name_regex(address: str) -> ParsedAddress:
    """
    Searches street (and street-prefix) from given string

    :param address: some string containing address with street and prefix (like "пр-кт")
    :return <ParsedAddress> like ParsedAddress("пр-кт", "Наименование проспекта", [])
    """
    regular_exp = rf"(.*?)({STREET_ELEMENTS})"
    logger.debug("Using regular expressions for street: '%s' | reg: '%s'", address, regular_exp)

    if match := re.search(regular_exp, address):
        street_name, prefix = match.groups()
        parsed_address = ParsedAddress(
            street_name=street_name.strip(), street_prefix=prefix, houses=[]
        )
    else:
        parsed_address = ParsedAddress(street_name=address, street_prefix="", houses=[])

    return parsed_address


def utcnow() -> datetime.datetime:
    """Just simple wrapper for deprecated datetime.utcnow"""
    return datetime.datetime.now(datetime.UTC)
