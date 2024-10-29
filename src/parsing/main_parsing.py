import pprint
import hashlib
import logging
import urllib.parse
from collections import defaultdict
from datetime import datetime, timedelta, date

import httpx
from lxml import html

from src.db.models import Address, DateRange
from src.utils import get_street_and_house, ADDRESS_DEFAULT_PATTERN
from src.config.app import RESOURCE_URLS, SupportedCity, SupportedService, DATA_PATH

logger = logging.getLogger("parsing.main")


class Parser:
    date_format = "%d.%m.%Y"
    address_pattern = ADDRESS_DEFAULT_PATTERN
    max_days_filter = 90

    def __init__(self, city: SupportedCity) -> None:
        self.urls = RESOURCE_URLS[city]
        self.city = city
        self.date_start = datetime.now().date()
        self.finish_time_filter = self.date_start + timedelta(days=self.max_days_filter)

    def parse(
        self, service: SupportedService, user_address: Address
    ) -> dict[Address, set[DateRange]]:
        """
        Allows to fetch shouting down info from supported service and format by requested address


        Args:
            service: requested Service
            user_address: current user's address

        Returns:
            dict with mapping: user-address -> list of dates
        """
        logger.debug(f"Parsing for service: {service} ({user_address})")
        parsed_data = self._parse_website(service, user_address) or {}
        logger.debug("Parsed data %s | \n%s", service, parsed_data)

        found_ranges: dict[Address, set[DateRange]] = {}
        for address, date_ranges in parsed_data.items():
            if address.matches(user_address):
                found_ranges[address] = date_ranges

        return found_ranges

    def _get_content(self, service: SupportedService, address: Address) -> str:
        url = self.urls[service].format(
            city="",
            street=urllib.parse.quote_plus(address.street.encode()) if address.street else "",
            date_start=self._format_date(self.date_start),
            date_finish=self._format_date(self.finish_time_filter),
        )
        tmp_file_path = (
            DATA_PATH / f"{service.lower()}_{hashlib.sha256(url.encode("utf-8")).hexdigest()}.html"
        )
        if tmp_file_path.exists():
            return tmp_file_path.read_text()

        logger.debug("Getting content for service: %s ...", url)
        with httpx.Client() as client:
            response = client.get(url)
            response_data = response.text

        tmp_file_path.touch()
        tmp_file_path.write_text(response_data)
        return response_data

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

        result = defaultdict(set)

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
                    street_name, houses = get_street_and_house(
                        pattern=self.address_pattern, address=raw_address
                    )
                    logger.debug(
                        "Parsing [%(service)s] Found record: raw: "
                        "%(raw_address)s | %(street_name)s | %(houses)s | %(start)s | %(end)s",
                        {
                            "service": service,
                            "raw_address": raw_address,
                            "street_name": street_name,
                            "houses": houses,
                            "start": start_time.isoformat() if start_time else "",
                            "end": end_time.isoformat() if end_time else "",
                        },
                    )
                    for house in houses:
                        address_key = Address(
                            city=self.city, street=street_name, house=house, raw=raw_address
                        )
                        result[address_key].add(DateRange(start_time, end_time))

        pprint.pprint(result, indent=4)
        print("======")
        return result

    @staticmethod
    def _format_date(date: datetime | date) -> str:
        return date.strftime("%d.%m.%Y")

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

    @staticmethod
    def _clear_string(src_string: str) -> str:
        return src_string.replace("\n", "").strip()


class HotWaterParser(Parser):

    def _parse_website(
        self,
        service: SupportedService,
        address: Address,
    ) -> dict[Address, set[DateRange]]:
        # TODO: use DI instead!
        html_content = self._get_content(service, address)
        tree = html.fromstring(html_content)
        rows = tree.xpath("//table/tbody/tr")
        if not rows:
            logger.info("No data found for service: %s", service)
            return {}

        result = defaultdict(set)

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
                    street_name, houses = get_street_and_house(
                        pattern=self.address_pattern, address=raw_address
                    )
                    logger.debug(
                        "Parsing [%(service)s] Found record: raw: "
                        "%(raw_address)s | %(street_name)s | %(houses)s | %(start)s | %(end)s",
                        {
                            "service": service,
                            "raw_address": raw_address,
                            "street_name": street_name,
                            "houses": houses,
                            "start": start_time.isoformat() if start_time else "",
                            "end": end_time.isoformat() if end_time else "",
                        },
                    )
                    for house in houses:
                        address_key = Address(
                            city=self.city, street=street_name, house=house, raw=raw_address
                        )
                        result[address_key].add(DateRange(start_time, end_time))

        pprint.pprint(result, indent=4)
        print("======")
        return result
