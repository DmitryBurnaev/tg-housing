import logging
import datetime
from operator import attrgetter
from typing import NamedTuple, Type

from src.config.app import DT_FORMAT, D_FORMAT
from src.config.constants import SupportedCity, SupportedService
from src.parsing.data_models import Address
from src.parsing.main_parsing import BaseParser

logger = logging.getLogger(__name__)


class ShutDownInfo(NamedTuple):
    start: datetime.datetime | datetime.date | None
    end: datetime.datetime | datetime.date | None
    raw_address: str
    city: SupportedCity
    error: str | None = None

    def __str__(self) -> str:
        if self.error:
            return f"{self.raw_address}: unable to get ({self.error})"

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
        result: list[ShutDownInfo] = []

        try:
            shutdowns = parser.parse(user_address=user_address)
        except Exception as exc:
            logger.exception("Could not fetch shutdowns: %r", exc)
            result.append(
                ShutDownInfo(
                    start=None,
                    end=None,
                    raw_address=address,
                    city=city,
                    error=str(exc),
                )
            )
            return result

        for address_, data_ranges in shutdowns.items():
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
    def for_addresses(
        cls,
        city: SupportedCity,
        addresses: list[str],
    ) -> list[ShutDownByServiceInfo]:
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
                if shutdowns := cls.for_address(city, address, service):
                    shutdown_info_list.append(
                        ShutDownByServiceInfo(
                            service=service, shutdowns=sorted(shutdowns, key=attrgetter("start"))
                        )
                    )
                    if shutdowns[0].error:
                        break

        return shutdown_info_list
