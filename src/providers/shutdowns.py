import datetime
from typing import NamedTuple, Type

from src.config.app import SupportedService, SupportedCity, DT_FORMAT, D_FORMAT
from src.parsing.data_models import Address
from src.parsing.main_parsing import BaseParser


class ShutDownInfo(NamedTuple):
    start: datetime.datetime | datetime.date | None
    end: datetime.datetime | datetime.date | None
    raw_address: str
    city: SupportedCity

    def __str__(self) -> str:
        return f"{self.raw_address}: {self.dt_format(self.start)} - {self.dt_format(self.end)}"

    @classmethod
    def dt_format(cls, dt: datetime.datetime | datetime.date | None) -> str:
        """String representation of datetime.datetime or datetime.date (showed in TG's message)"""

        if dt is None:
            return "-"

        if isinstance(dt, datetime.datetime):
            return dt.strftime(DT_FORMAT)

        return dt.strftime(D_FORMAT)

    @property
    def start_repr(self) -> str:
        return self.dt_format(self.start)

    @property
    def end_repr(self) -> str:
        return self.dt_format(self.end)


class ShutDownByServiceInfo(NamedTuple):
    service: SupportedService
    shutdowns: list[ShutDownInfo]


class ShutDownProvider:
    """Collects info, given from parsers by specific address"""

    @classmethod
    def for_address(
        cls, city: SupportedCity, address: str, service: SupportedService
    ) -> list[ShutDownInfo]:
        user_address = Address.from_string(raw_address=address)
        parser_class: Type[BaseParser] = BaseParser.get_parsers()[service]
        parser = parser_class(city)
        shutdowns = parser.parse(user_address=user_address)
        print(f"{shutdowns=}")
        result: list[ShutDownInfo] = []

        for address_, data_ranges in shutdowns.items():
            print(address, data_ranges)
            for data_range in data_ranges:
                result.append(
                    ShutDownInfo(
                        start=data_range.start,
                        end=data_range.end,
                        raw_address=address_.raw,
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
            print(f"{service=}")
            for address in addresses:
                if shutdowns := cls.for_address(SupportedCity.SPB, address, service):
                    shutdown_info_list.append(
                        ShutDownByServiceInfo(service=service, shutdowns=shutdowns)
                    )

        return shutdown_info_list
