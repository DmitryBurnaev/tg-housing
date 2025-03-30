from typing import Any

import pytest

from src.utils import parse_address


@pytest.mark.parametrize(
    "address, expected_result",
    [
        (
            "Загадочный Инопланетянин пр., д.75 корп.1",
            {"street_prefix": "пр-кт", "street_name": "Загадочный Инопланетянин", "houses": [75]},
        ),
        (
            "пр-кт Загадочный Инопланетянин д.175 корп.1",
            {"street_prefix": "пр-кт", "street_name": "Загадочный Инопланетянин", "houses": [175]},
        ),
        (
            "Загадочный Инопланетянин         , дом 75",
            {"street_prefix": "ул", "street_name": "Загадочный Инопланетянин", "houses": [75]},
        ),
        (
            "ул. Загадочный, д.75",
            {"street_prefix": "ул", "street_name": "Загадочный", "houses": [75]},
        ),
        (
            "тракт Загадочный, д.75",
            {"street_prefix": "тракт", "street_name": "Загадочный", "houses": [75]},
        ),
        (
            "Загадочный Инопланетянин пр., д.75-79",
            {
                "street_prefix": "пр-кт",
                "street_name": "Загадочный Инопланетянин",
                "houses": [75, 76, 77, 78, 79],
            },
        ),
        (
            "пр. Загадочный Инопланетянин 79",
            {"street_prefix": "пр-кт", "street_name": "Загадочный Инопланетянин", "houses": [79]},
        ),
        (
            "Avenue Name пр., дом 75",
            {"street_prefix": "пр-кт", "street_name": "Avenue Name", "houses": [75]},
        ),
        (
            "Invalid Address Format",
            {"street_prefix": "ул", "street_name": "Invalid Address Format", "houses": []},
        ),
    ],
)
def test_extract_street_and_house_info(address: str, expected_result: dict[str, Any]) -> None:
    parsed_address = parse_address(address)
    actual_result = {
        "street_prefix": parsed_address.street_prefix,
        "street_name": parsed_address.street_name,
        "houses": parsed_address.houses,
    }
    assert actual_result == expected_result
