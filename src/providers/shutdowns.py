import datetime
from typing import NamedTuple

from src.config.app import SupportedService, SupportedCity
from src.db.models import Address
from src.parsing.main_parsing import BaseParser


class ShutDownInfo(NamedTuple):
    start: datetime.datetime
    end: datetime.datetime
    raw_address: str
    city: SupportedCity

    def __str__(self) -> str:
        return f"{self.raw_address}: {self._dt_format(self.start)} - {self._dt_format(self.end)}"

    @staticmethod
    def _dt_format(dt: datetime.datetime) -> str:
        return dt.strftime("%d.%m.%Y %H:%M")


class ShutDownByServiceInfo(NamedTuple):
    service: SupportedService
    shutdowns: list[ShutDownInfo]


class ShutDownProvider:
    @classmethod
    def for_address(cls, address: str, service: SupportedService) -> list[ShutDownInfo]:
        user_address = Address.from_string(raw_address=address)
        parser_class = BaseParser.get_parsers()[service]
        shutdowns = parser_class.parse(user_address=user_address)
        print(shutdowns)
        result: list[ShutDownInfo] = []

        for address, data_ranges in shutdowns.items():
            print(address, data_ranges)
            for data_range in data_ranges:
                result.append(
                    ShutDownInfo(
                        start=data_range.start,
                        end=data_range.end,
                        raw_address=address.raw,
                        city=user_address.city,
                    )
                )

        return result

    @classmethod
    def for_addresses(cls, addresses: list[str]) -> list[ShutDownByServiceInfo]:
        """Returns a structure with ShutDownInfo instances
        Examples:
        [
            ShutDownByServiceInfo(
                service=SupportedService.ELECTRICITY,
                shutdowns=[
                    ShutDownInfo(start=data_range.start, end=data_range.end, address=address.raw)
                ]
            )
        ]

        """
        shutdown_info_list = []
        for service in SupportedService.members():
            for address in addresses:
                if shutdowns := cls.for_address(address, service):
                    shutdown_info_list.append(
                        ShutDownByServiceInfo(service=service, shutdowns=shutdowns)
                    )

        return shutdown_info_list
