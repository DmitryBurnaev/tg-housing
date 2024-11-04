import pytest

from src.utils import parse_address


@pytest.mark.parametrize(
    "address, expected_result",
    [
        (
            "Avenue Name пр., д.75 корп.1",
            {"street_prefix": "", "street_name": "Avenue Name пр.", "houses": [75]},
        ),
        (
            "пр. Avenue Name         , д.75 корп.1",
            {"street_prefix": "пр", "street_name": "Avenue Name", "houses": [75]},
        ),
        (
            "ул. Street Name, д.75",
            {"street_prefix": "ул", "street_name": "Street Name", "houses": [75]},
        ),
        (
            "тракт Street Name, д.75",
            {"street_prefix": "тракт", "street_name": "Street Name", "houses": [75]},
        ),
        (
            "Avenue Name пр., д.75-79",
            {"street_prefix": "", "street_name": "Avenue Name пр.", "houses": [75, 76, 77, 78, 79]},
        ),
        (
            "Avenue Name пр., д.79",
            {"street_prefix": "", "street_name": "Avenue Name пр.", "houses": [79]},
        ),
        (
            "Avenue Name пр., дом 75",
            {"street_prefix": "", "street_name": "Avenue Name пр.", "houses": [75]},
        ),
        (
            "Invalid Address Format",
            {"street_prefix": "", "street_name": "Invalid Address Format", "houses": []},
        ),
    ],
)
def test_extract_street_and_house_info(address, expected_result):
    parsed_address = parse_address(address)
    actual_result = {
        "street_prefix": parsed_address.street_prefix,
        "street_name": parsed_address.street_name,
        "houses": parsed_address.houses,
    }
    assert actual_result == expected_result
