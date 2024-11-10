import abc
import pprint
import hashlib
import logging
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta, date, timezone
from typing import ClassVar, Type

import httpx
from lxml import html

from src.db.models import Address, DateRange
from src.utils import parse_address, ADDRESS_DEFAULT_PATTERN
from src.config.app import RESOURCE_URLS, SupportedCity, SupportedService, DATA_PATH

logger = logging.getLogger("parsing.main")


class BaseParser(abc.ABC):
    date_format = "%d.%m.%Y"
    address_pattern = ADDRESS_DEFAULT_PATTERN
    max_days_filter = 90
    service: ClassVar[SupportedService] = NotImplemented

    def __init__(self, city: SupportedCity) -> None:
        self.urls = RESOURCE_URLS[city]
        self.city = city
        self.date_start = datetime.now().date()
        self.finish_time_filter = self.date_start + timedelta(days=self.max_days_filter)

    def parse(self, user_address: Address) -> dict[Address, set[DateRange]]:
        """
        Allows to fetch shouting down info from supported service and format by requested address


        Args:
            user_address: current user's address

        Returns:
            dict with mapping: user-address -> list of dates
        """
        logger.debug(f"Parsing for service: {self.service} ({user_address})")
        parsed_data: dict[Address, set[DateRange]] = self._parse_website(self.service, user_address)
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
            return f"{service.lower()}_{dt}_{hashlib.sha256(url.encode("utf-8")).hexdigest()}.html"

        url = self.urls[service].format(
            city="",
            street_name=urllib.parse.quote_plus((address.street_name or "").encode()),
            street_prefix=urllib.parse.quote_plus((address.street_prefix or "").encode()),
            house=address.house if address.house else "",
            date_start=self._format_date(self.date_start),
            date_finish=self._format_date(self.finish_time_filter),
        )
        tmp_file_path = DATA_PATH / cashed_filename(url)
        if tmp_file_path.exists():
            return tmp_file_path.read_text()

        logger.debug("Getting content for service: %s ...", url)
        with httpx.Client() as client:
            response = client.get(url)
            response_data = response.text

        tmp_file_path.touch()
        tmp_file_path.write_text(response_data)
        return response_data

    @abc.abstractmethod
    def _parse_website(self, service: str, user_address: Address) -> dict[Address, set[DateRange]]:
        pass

    @staticmethod
    def _format_date(date: datetime | date) -> str:
        return date.strftime("%d.%m.%Y")

    @staticmethod
    def _clear_string(src_string: str) -> str:
        return src_string.replace("\n", "").replace(" ", "").strip()

    @classmethod
    def get_parsers(cls) -> dict[SupportedService, Type["BaseParser"]]:
        return {subclass.service: subclass for subclass in cls.__subclasses__()}


class SPBElectricityParser(BaseParser):
    service = SupportedService.ELECTRICITY

    def _parse_website(
        self,
        service: SupportedService,
        address: Address,
    ) -> dict[Address, set[DateRange]]:
        """
        Parses websites by URL's provided in params

        :param service: provide site's address which should be parsed
        :return: given data from website
        """

        html_content = self._get_content(service, address)
        tree = html.fromstring(html_content)
        rows = tree.xpath("//table/tbody/tr")
        if not rows:
            logger.info("No data found for service: %s", service)
            return {}

        result: defaultdict[Address, set] = defaultdict(set)

        for row in rows:
            if row_streets := row.xpath(".//td[@class='rowStreets']"):
                addresses = row_streets[0].xpath(".//span/text()")
                dates = row.xpath("td/text()")[4:8]
                date_start, time_start, date_end, time_end = map(self._clear_string, dates)

                if len(addresses) == 1:
                    addresses = addresses[0]
                else:
                    logger.warning(
                        "Streets count more than 1: %(service)s | %(address)s",
                        {"service": service, "address": address},
                    )
                    addresses = ",".join(addresses)

                start_time = self._prepare_time(date_start, time_start)
                end_time = self._prepare_time(date_end, time_end)
                for raw_address in addresses.split(","):
                    raw_address = self._clear_string(raw_address)
                    parsed_address = parse_address(
                        pattern=self.address_pattern, address=raw_address
                    )
                    logger.debug(
                        "Parsing [%(service)s] Found record: raw: "
                        "%(raw_address)s | %(street_name)s | %(houses)s | %(start)s | %(end)s",
                        {
                            "service": service,
                            "raw_address": raw_address,
                            "street_name": parsed_address.street_name,
                            "houses": parsed_address.houses,
                            "start": start_time.isoformat() if start_time else "",
                            "end": end_time.isoformat() if end_time else "",
                        },
                    )
                    for house in parsed_address.houses:
                        address_key = Address(
                            city=self.city,
                            street_name=parsed_address.street_name,
                            street_prefix=parsed_address.street_prefix,
                            house=house,
                            raw=raw_address,
                        )
                        result[address_key].add(DateRange(start_time, end_time))

        pprint.pprint(result, indent=4)
        print("======")
        return result

    def _prepare_time(self, date: str, time: str) -> datetime | None:
        date = self._clear_string(date)
        time = self._clear_string(time)
        if not (date and time):
            logger.warning("Missing date or time: date='%s' | time='%s'", date, time)
            return None

        try:
            result = datetime.strptime(f"{date}T{time}", "%d-%m-%YT%H:%M")
        except ValueError:
            logger.warning("Incorrect date / time: date='%s' | time='%s'", date, time)
            return None

        return result


class SPBHotWaterParser(BaseParser):
    service = SupportedService.HOT_WATER

    def _parse_website(
        self,
        service: SupportedService,
        address: Address,
    ) -> dict[Address, set[DateRange]]:
        html_content = self._get_content(service, address)
        tree = html.fromstring(html_content)
        rows = tree.xpath("//table[@class='graph']/tbody/tr")
        if not rows:
            logger.info("No data found for service: %s", service)
            return {}

        result = defaultdict(set)

        for row in rows:
            if row.xpath(".//td"):
                row_data = row.xpath(".//td/text()")
                try:
                    logger.debug(
                        "Parsing [%(service)s] Found record: row_data: %(row_data)s",
                        {
                            "service": self.service,
                            "row_data": row_data,
                        },
                    )
                    (_, district, street, house, liter, period_1, period_2) = row_data
                except IndexError:
                    logger.warning(
                        "Parsing [%(service)s] Found unparsable row: %(row_data)s",
                        {
                            "service": self.service,
                            "row_data": row_data,
                        },
                    )
                    continue
                else:
                    logger.debug(
                        "Parsing [%(service)s] Found district: %(district)s | street: %(street)s "
                        "| house: %(house)s | period_1: %(period_1)s | period_2: %(period_2)s",
                        {
                            "service": self.service,
                            "district": district,
                            "street": street,
                            "house": house,
                            "period_1": period_1,
                            "period_2": period_2,
                        },
                    )

                for period in (period_1, period_2):
                    start_dt, finish_dt = self._prepare_dates(period)
                    logger.debug(
                        "Parsing [%(service)s] Found record: "
                        "%(street)s | %(house)s | %(start)s | %(end)s",
                        {
                            "service": service,
                            "street": street,
                            "house": house,
                            "start": start_dt.isoformat() if start_dt else "",
                            "end": finish_dt.isoformat() if finish_dt else "",
                        },
                    )
                    address_key = Address(
                        city=self.city, street_name=street, house=house, raw=address.raw
                    )
                    result[address_key].add(DateRange(start_dt, finish_dt))
            else:
                logger.info(
                    "Parsing [%(service)s] No Found data for address: %(address)s",
                    {
                        "service": self.service,
                        "address": address,
                    },
                )

        return result

    def _prepare_dates(self, period: str) -> tuple[datetime | None, datetime | None]:
        raw_date_1, raw_date_2 = period.split(" - ")

        def get_dt(raw_date: str) -> datetime | None:
            raw_date = self._clear_string(raw_date)
            try:
                result = datetime.strptime(raw_date, "%d.%m.%Y")
            except ValueError:
                logger.warning("Incorrect date / time: date='%s'", raw_date)
                return None

            return result

        start_dt = get_dt(raw_date_1)
        finish_dt = get_dt(raw_date_2)
        return start_dt, finish_dt
