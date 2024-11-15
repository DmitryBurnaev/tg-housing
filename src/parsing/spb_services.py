import locale
import pprint
from contextlib import contextmanager
from datetime import datetime
from collections import defaultdict
from functools import wraps
from typing import NamedTuple

from lxml import html

from src.config.app import SupportedService
from src.db.models import Address, DateRange
from src.parsing.main_parsing import BaseParser, logger
from src.utils import parse_address

__all__ = (
    "SPBElectricityParser",
    "SPBHotWaterParser",
    "SPBColdWaterParser",
)


def set_locale_decorator(func):
    """ Temp added ru local for correct parsing datetimes """
    @wraps(func)
    def wrapper(*args, **kwargs):
        old_locale = locale.getlocale(locale.LC_ALL)
        try:
            locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
            result = func(*args, **kwargs)
        finally:
            locale.setlocale(locale.LC_ALL, old_locale)
        return result

    return wrapper


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


class ColdWaterRecord(NamedTuple):
    street: str
    period_start: str
    period_end: str


class SPBColdWaterParser(BaseParser):
    service = SupportedService.COLD_WATER

    def _parse_website(
        self,
        service: SupportedService,
        address: Address,
    ) -> dict[Address, set[DateRange]]:
        html_content = self._get_content(service, address)
        tree = html.fromstring(html_content)
        rows = tree.xpath("//div[@class='listplan-item']")
        if not rows:
            logger.info("No data found for service: %s", service)
            return {}

        result = defaultdict(set)

        for row in rows:
            if not (row_data := self._extract_info_tags(row)):
                logger.debug(
                    "Parsing [%(service)s] Found unparsable row: %(row_data)s",
                    {
                        "service": self.service,
                        "row_data": row.text_content(),
                    }
                )
                continue

            try:
                logger.debug(
                    "Parsing [%(service)s] Found record: row_data: %(row_data)r",
                    {
                        "service": self.service,
                        "row_data": row_data,
                    },
                )
                # street, period_1 = row_data
            except IndexError:
                logger.warning(
                    "Parsing [%(service)s] Found unparsable row: %(row_data)r",
                    {
                        "service": self.service,
                        "row_data": row_data,
                    },
                )
                continue
            else:
                logger.debug(
                    "Parsing [%(service)s] Found street: %(street)s "
                    "| period_1: %(period_1)s | period_2: %(period_2)s",
                    {
                        "service": self.service,
                        "street": row_data.street,
                        "period_1": row_data.period_start,
                        "period_2": row_data.period_end,
                    },
                )

            start_dt, finish_dt = self._prepare_dates(row_data.period_start, row_data.period_end)
            logger.debug(
                "Parsing [%(service)s] Found record: "
                "%(street)s | %(start)s | %(end)s",
                {
                    "service": self.service,
                    "street": row_data.street,
                    "start": start_dt.isoformat() if start_dt else "",
                    "end": finish_dt.isoformat() if finish_dt else "",
                },
            )
            if address.street_name in row_data.street:
                address_key = Address(
                    city=self.city,
                    street_name=address.street_name,
                    raw=row_data.street,
                )
                result[address_key].add(DateRange(start_dt, finish_dt))

        if not result:
            logger.info(
                "Parsing [%(service)s] No Found data for address: %(address)s",
                {
                    "service": self.service,
                    "address": address,
                },
            )

        return result

    @set_locale_decorator
    def _prepare_dates(self, period_1: str, period_2: str) -> tuple[datetime | None, datetime | None]:
        raw_date_1, raw_date_2 = period_1, period_2

        def get_dt(raw_date: str) -> datetime | None:
            try:
                result = datetime.strptime(raw_date.strip(), "%d %B %Y %H:%M")
            except ValueError:
                logger.warning("Incorrect date / time: date='%s'", raw_date)
                return None

            return result

        start_dt = get_dt(raw_date_1)
        finish_dt = get_dt(raw_date_2)
        return start_dt, finish_dt

    @staticmethod
    def _extract_info_tags(row: html.HtmlElement) -> ColdWaterRecord | None:
        if not (info_tags := row.xpath(".//div//strong")):
            logger.debug(
                "Parsing [%(service)s] Found unparsable row: %(row)s",
                {
                    "service": SupportedService.COLD_WATER,
                    "row": row.text_content(),
                }
            )
            return None

        shutdown_period_1: str | None = None
        shutdown_period_2: str | None = None
        shutdown_street: str | None = None
        # print("====")
        for info_tag in info_tags:
            # print(info_tag.text)
            if "начало" in info_tag.text.lower():
                shutdown_period_1 = info_tag.tail.strip()
            elif "окончание" in info_tag.text.lower():
                shutdown_period_2 = info_tag.tail.strip()
            elif "адреса отключаемых объектов" in info_tag.text.lower():
                shutdown_street = info_tag.tail.strip()

            if all([shutdown_period_1, shutdown_period_2, shutdown_street]):
                break
        else:
            return None

        return ColdWaterRecord(
            period_start=shutdown_period_1,
            period_end=shutdown_period_2,
            street=shutdown_street,
        )
