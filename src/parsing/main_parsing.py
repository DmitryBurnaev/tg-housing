import abc
import hashlib
import logging
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from typing import ClassVar, Pattern

import httpx

from src.config.app import (
    DATA_PATH,
    SSL_REQUEST_VERIFY,
    PARSE_DAYS_BEFORE,
    PARSE_DAYS_AFTER,
)
from src.config.constants import SupportedCity, SupportedService, RESOURCE_URLS
from src.parsing.data_models import Address, DateRange
from src.utils import ADDRESS_DEFAULT_PATTERN, utcnow

logger = logging.getLogger("parsing.main")


class ParsingError(Exception):
    message: str = "Unknown parsing error"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r})"


class SkipParsingError(ParsingError):
    message: str = "Skipping parsing"

    def __init__(self, service: SupportedService, address: Address, message: str) -> None:
        self.service = service
        self.address = address
        self.message = message

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(message={self.message!r}, address={self.address!r}, "
            f"service={self.service!r})"
        )

    def __str__(self) -> str:
        return (
            f"SkipParsingError: {self.message} (address={self.address!r}, service={self.service!r})"
        )


class BaseParser(abc.ABC):
    """
    Base class for all parsers. Provides logic for fetching and parse specific
    (overrides by child class)
    """

    date_format: ClassVar[str] = "%d.%m.%Y"
    address_pattern: ClassVar[Pattern[str]] = ADDRESS_DEFAULT_PATTERN
    days_before: ClassVar[int] = PARSE_DAYS_BEFORE
    days_after: ClassVar[int] = PARSE_DAYS_AFTER
    service: ClassVar[SupportedService] = NotImplemented

    def __init__(self, city: SupportedCity, verbose: bool = False) -> None:
        self.urls: dict[SupportedService, str] | None = RESOURCE_URLS.get(city)
        self.city = city
        self.date_start = utcnow().date() - timedelta(days=self.days_before)
        self.finish_time_filter = self.date_start + timedelta(days=self.days_after)
        self.verbose: bool = verbose

    def parse(self, user_address: Address) -> dict[Address, set[DateRange]]:
        """
        Allows to fetch shouting down info from supported service and format by requested address


        Args:
            user_address: current user's address

        Returns:
            dict with mapping: user-address -> list of dates
        """
        logger.info(f"Parsing for service: {self.service} ({user_address})")
        try:
            content: str = self._get_content(self.service, user_address)
            parsed_data: dict[Address, set[DateRange]] = self._parse_website(
                service=self.service,
                address=user_address,
                fetched_content=content,
            )
        except SkipParsingError as exc:
            logger.debug(f"SkipParsing: {exc}")
            return {}

        except ParsingError as exc:
            logger.error("Unable parsing: %r", exc)
            return {}

        logger.debug(
            "Parsed %(service)s | \n%(parsed_data)s",
            {
                "service": self.service,
                "parsed_data": parsed_data,
            },
        )

        found_ranges: dict[Address, set[DateRange]] = {}
        for address, date_ranges in parsed_data.items():
            if address.matches(user_address):
                found_ranges[address] = date_ranges

        return found_ranges

    def _get_content(self, service: SupportedService, address: Address) -> str:
        def cashed_filename(url: str) -> str:
            dt = datetime.now(tz=timezone.utc).date().isoformat()
            return f"{service.lower()}_{dt}_{hashlib.sha256(url.encode('utf-8')).hexdigest()}.html"

        if not self.urls:
            logger.info("No urls available for city %s detected. Skip parsing", self.city)
            raise SkipParsingError(self.service, address, "No urls available")

        url = self.urls[service].format(
            city="",
            street_name=urllib.parse.quote_plus((address.street_name or "").encode()),
            street_prefix=urllib.parse.quote_plus((address.street_prefix or "").encode()),
            house=address.house if address.house else "",
            date_start=self._format_date(self.date_start),
            date_finish=self._format_date(self.finish_time_filter),
        )
        tmp_file_path = DATA_PATH / "sites" / cashed_filename(url)
        if tmp_file_path.exists():
            logger.debug(
                "File %(tmp_file_path)s exists (content from %(url)s",
                {
                    "url": url,
                    "tmp_file_path": tmp_file_path,
                },
            )
            return tmp_file_path.read_text()

        logger.debug("Getting content for service: %s ...", url)
        with httpx.Client(verify=SSL_REQUEST_VERIFY) as client:
            response = client.get(url)
            response_data = response.text

        tmp_file_path.touch()
        tmp_file_path.write_text(response_data)
        return response_data

    @abc.abstractmethod
    def _parse_website(
        self, service: SupportedService, address: Address, fetched_content: str
    ) -> dict[Address, set[DateRange]]:
        pass

    @staticmethod
    def _format_date(date: datetime | date) -> str:
        return date.strftime("%d.%m.%Y")

    @staticmethod
    def _clear_string(src_string: str | None) -> str:
        if src_string is None:
            return ""
        return src_string.replace("\n", "").strip()

    @classmethod
    def get_parsers(cls) -> dict[SupportedService, type["BaseParser"]]:
        return {subclass.service: subclass for subclass in cls.__subclasses__()}
