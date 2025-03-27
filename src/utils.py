import datetime
import re
import logging
from typing import NamedTuple

logger = logging.getLogger(__name__)

STREET_ELEMENTS = r"""
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
ш\.?""".replace(
    "\n", ""
)

ADDRESS_DEFAULT_PATTERN = re.compile(
    rf"^(?P<street_prefix>{STREET_ELEMENTS})?\s*(?P<street_name>[\w\s.]+?),?\s(?:д\.?|дом)?\s*(?P<start_house>\d+)(?:[-–](?P<end_house>\d+))?(?:\sкорп\.\d+)?"
)
REPLACE_STREET_PREFIX: dict[str, str] = {
    "пр": "пр-кт",
    "пр-т": "пр-кт",
}
DEFAULT_STREET_PREFIX = "пр-кт"


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
    if match := (pattern or ADDRESS_DEFAULT_PATTERN).search(address):
        if street_prefix := match.group("street_prefix"):
            street_prefix = street_prefix.strip().removesuffix(".")
            street_prefix = REPLACE_STREET_PREFIX.get(street_prefix, street_prefix)
        else:
            logger.debug("Using default street prefix")
            street_prefix = DEFAULT_STREET_PREFIX

        street_name = match.group("street_name").strip()
        start_house = int(match.group("start_house"))
        end_house = int(match.group("end_house")) if match.group("end_house") else start_house
        houses = list(range(start_house, end_house + 1))
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
