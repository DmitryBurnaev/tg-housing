import re
from typing import NamedTuple

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
пр\.?|
пл\.?|
пр-д\.?|
пр-т\.?|пр-кт\.?|
пр-ка\.?|
пр-лок\.?|
проул\.?|
рзд\.?|
ряд\.?|
с-р\.?|
с-к\.?|
сзд\.?|
тракт\.?|
туп\.?|
ул\.?|
ш\.?""".replace("\n", "")

ADDRESS_DEFAULT_PATTERN = re.compile(
    rf"^(?P<street_prefix>{STREET_ELEMENTS})?\s*(?P<street_name>[\w\s.]+?),?\s(?:д\.?|дом)?\s*(?P<start_house>\d+)(?:[-–](?P<end_house>\d+))?(?:\sкорп\.\d+)?"
)
REPLACE_STREET_PREFIX: dict[str, str] = {
    "пр": "пр-кт",
    "пр-т": "пр-кт",
}


class ParsedAddress(NamedTuple):
    street_prefix: str
    street_name: str
    houses: list[int]
    start_house: int | None = None
    end_house: int | None = None

    def __str__(self) -> str:
        houses = ",".join(map(str, self.houses))
        return f"{self.street_prefix}. {self.street_name}, д. {houses}"

    @property
    def completed(self):
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
    :return <tuple> like ("My Street", [12]) or ("My Street", [12, 13, 14, 15])
    """
    if match := (pattern or ADDRESS_DEFAULT_PATTERN).search(address):
        if street_prefix := match.group("street_prefix"):
            street_prefix = street_prefix.strip().removesuffix(".")
            street_prefix = REPLACE_STREET_PREFIX.get(street_prefix, street_prefix)

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
