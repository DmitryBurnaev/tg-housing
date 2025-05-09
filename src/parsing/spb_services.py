from datetime import datetime, date
from collections import defaultdict
from typing import NamedTuple, cast, Sequence

from lxml import html

from src.decorators import set_locale_decorator
from src.config.constants import SupportedService
from src.parsing.data_models import Address, DateRange
from src.parsing.main_parsing import BaseParser, logger
from src.utils import parse_address, ParsedAddress

__all__ = (
    "SPBElectricityParser",
    "SPBHotWaterParser",
    "SPBColdWaterParser",
)
SeqHTML = Sequence[html.HtmlElement]


class SPBElectricityParser(BaseParser):
    service = SupportedService.ELECTRICITY

    def _parse_website(
        self,
        service: SupportedService,
        address: Address,
        fetched_content: str,
    ) -> dict[Address, set[DateRange]]:
        """
        Parses websites by URL's provided in params

        :param service: provide site's address which should be parsed
        :return: given data from website
        """

        tree: html.HtmlElement = html.fromstring(fetched_content)
        rows: SeqHTML = cast(SeqHTML, tree.xpath("//table/tbody/tr"))
        if not rows:
            logger.info("No data found for service: %s", service)
            return {}

        result: defaultdict[Address, set[DateRange]] = defaultdict(set)

        for row in rows:
            row_streets: SeqHTML = cast(SeqHTML, row.xpath(".//td[@class='rowStreets']"))
            if not row_streets:
                logger.debug("No data found for row: %s", row)
                continue

            raw_addresses: list[str] = cast(list[str], row_streets[0].xpath(".//span/text()"))
            dates_range: list[html.HtmlElement] = cast(list[str], row.xpath("td"))[3:7]
            dates: list[str | None] = [td.text for td in dates_range]
            date_start, time_start, date_end, time_end = map(self._clear_string, dates)

            if len(raw_addresses) > 1:
                logger.debug(
                    "Parsing [%(service)s] Streets count > 1: %(address)s | %(raw_addresses)s)",
                    {"service": service, "address": address, "raw_addresses": raw_addresses},
                )

            start_time = self._prepare_time(date_start, time_start)
            end_time = self._prepare_time(date_end, time_end)
            for raw_address in raw_addresses:
                raw_address = self._clear_string(raw_address)
                parsed_address = parse_address(pattern=self.address_pattern, address=raw_address)
                logger.debug(
                    "Parsing [%(service)s] Found raw: "
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
                if not parsed_address.houses:
                    logger.warning(
                        "Parsing [%(service)s] Not found houses for parsed raw: '%(raw_address)s' ",
                        {"service": service, "raw_address": raw_address},
                    )
                    continue

                for house in parsed_address.houses:
                    address_key = Address(
                        city=self.city,
                        street_name=parsed_address.street_name,
                        street_prefix=parsed_address.street_prefix,
                        house=house,
                        raw=raw_address,
                    )
                    date_range = DateRange(start_time, end_time)
                    result[address_key].add(date_range)
                    logger.debug(
                        "Parsing [%(service)s] Found address key: %(address_key)s | %(date_range)s",
                        {"service": service, "address_key": address_key, "date_range": date_range},
                    )

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
        fetched_content: str,
    ) -> dict[Address, set[DateRange]]:
        tree = html.fromstring(fetched_content)
        rows: SeqHTML = cast(SeqHTML, tree.xpath("//table[@class='graph']/tbody/tr"))
        if not rows:
            logger.info(
                "Parsing [%(service)s] No information rows found ", {"service": self.service}
            )
            return {}

        result = defaultdict(set)

        for row in rows:
            if row.xpath(".//td"):
                row_data: list[str] = cast(list[str], row.xpath(".//td/text()"))
                try:
                    logger.debug(
                        "Parsing [%(service)s] Found record: row_data: %(row_data)s",
                        {
                            "service": self.service,
                            "row_data": row_data,
                        },
                    )
                    (_, district, street, raw_house, *raw_liters, period_1, period_2) = row_data
                    street = self._clear_string(street)
                    liter = "".join(raw_liters)
                    house = int(raw_house)
                except (IndexError, ValueError) as exc:
                    logger.warning(
                        "Parsing [%(service)s] Found unparsable row: %(row_data)s | error: %(exc)s",
                        {
                            "service": self.service,
                            "row_data": row_data,
                            "exc": exc,
                        },
                    )
                    continue
                else:
                    raw_address = f"{street}, {house} {liter}"
                    logger.debug(
                        "Parsing [%(service)s] Found district: %(district)s | street: %(street)s "
                        "| house: %(house)s | liter: %(liter)s"
                        " | period_1: %(period_1)s | period_2: %(period_2)s",
                        {
                            "service": self.service,
                            "district": district,
                            "street": street,
                            "house": house,
                            "liter": liter,
                            "period_1": period_1,
                            "period_2": period_2,
                        },
                    )

                parsed_street: ParsedAddress = parse_address(street)
                for period in (period_1, period_2):
                    start_dt, finish_dt = self._prepare_dates(period)
                    logger.debug(
                        "Parsing [%(service)s] Found record: "
                        "%(street)s | %(house)s | %(start)s | %(end)s",
                        {
                            "service": service,
                            "street": parsed_street,
                            "house": house,
                            "start": start_dt.isoformat() if start_dt else "",
                            "end": finish_dt.isoformat() if finish_dt else "",
                        },
                    )
                    address_key = Address(
                        city=self.city,
                        street_name=parsed_street.street_name,
                        street_prefix=parsed_street.street_prefix,
                        house=house,
                        raw=raw_address,
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

    def _prepare_dates(self, period: str) -> tuple[date | None, date | None]:
        raw_date_1, raw_date_2 = period.split(" - ")

        def get_dt(raw_date: str) -> date | None:
            raw_date = self._clear_string(raw_date)
            try:
                result = datetime.strptime(raw_date, "%d.%m.%Y").date()
            except ValueError as exc:
                logger.warning("Incorrect date / time: date='%s' (%s)", raw_date, exc)
                return None

            return result

        start_dt, finish_dt = get_dt(raw_date_1), get_dt(raw_date_2)
        if start_dt:
            start_dt = datetime.combine(start_dt, datetime.min.time())
        if finish_dt:
            finish_dt = datetime.combine(finish_dt, datetime.max.time())

        return start_dt, finish_dt


class ColdWaterRecord(NamedTuple):
    street: str | None
    period_start: str | None
    period_end: str | None


class SPBColdWaterParser(BaseParser):
    service = SupportedService.COLD_WATER

    def _parse_website(
        self,
        service: SupportedService,
        address: Address,
        fetched_content: str,
    ) -> dict[Address, set[DateRange]]:
        tree = html.fromstring(fetched_content)
        rows: SeqHTML = cast(SeqHTML, tree.xpath("//div[@class='listplan-item']"))
        if not rows:
            logger.info("Parsing [%(service)s] No data found for service", service)
            return {}

        result = defaultdict(set)

        for row in rows:
            if not (row_data := self._extract_info_tags(row)):
                logger.debug(
                    "Parsing [%(service)s] Found unparsable row: %(row_data)s",
                    {
                        "service": self.service,
                        "row_data": row.text_content().replace("\n", " | "),
                    },
                )
                continue

            logger.debug(
                "Parsing [%(service)s] Found record: row_data: %(row_data)r",
                {
                    "service": self.service,
                    "row_data": row_data,
                },
            )

            start_dt, finish_dt = self._prepare_dates(row_data.period_start, row_data.period_end)
            logger.debug(
                "Parsing [%(service)s] Found record: %(street)s | %(start)s | %(end)s",
                {
                    "service": self.service,
                    "street": row_data.street,
                    "start": start_dt.isoformat() if start_dt else "",
                    "end": finish_dt.isoformat() if finish_dt else "",
                },
            )
            if not row_data.street:
                logger.debug(
                    "Parsing [%(service)s] No Street: %(row_data)s",
                    {
                        "service": self.service,
                        "row_data": row_data,
                    },
                )
                continue

            if address.street_name.lower() in row_data.street.lower():
                address_key = Address(
                    city=self.city,
                    raw=row_data.street,
                    street_name=address.street_name,
                    street_prefix=address.street_prefix,
                    house=address.house,
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
    def _prepare_dates(
        self,
        period_1: str | None,
        period_2: str | None,
    ) -> tuple[datetime | date | None, datetime | date | None]:
        raw_date_1, raw_date_2 = period_1, period_2

        def get_dt(raw_date: str | None) -> datetime | date | None:
            if not raw_date:
                logger.warning(
                    "Missing raw_date (None): period_1=%(period_1)s | period_2=%(period_2)s",
                    {"period_1": period_1, "period_2": period_2},
                )
                return None

            try:
                return datetime.strptime(raw_date.strip(), "%d %B %Y %H:%M")
            except ValueError:
                try:
                    return datetime.strptime(raw_date.strip(), "%d %B %Y").date()
                except Exception as exc:
                    logger.error(
                        "Parsing [COLD_WATER] Unable to get date / time '%(raw_date)s' "
                        "period_1 = '%(period_1)s' | period_2 = '%(period_2)s' (error: %(exc)s)",
                        {
                            "service": self.service,
                            "raw_date": raw_date,
                            "period_1": period_1,
                            "period_2": period_2,
                            "exc": exc,
                        },
                    )

            return None

        start_dt = get_dt(raw_date_1)
        finish_dt = get_dt(raw_date_2)
        return start_dt, finish_dt

    @staticmethod
    def _extract_info_tags(row: html.HtmlElement) -> ColdWaterRecord | None:
        if not (info_tags := row.xpath(".//div//strong")):
            logger.debug(
                "Parsing [%(service)s] No info tags: %(row)s",
                {
                    "service": SupportedService.COLD_WATER,
                    "row": row.text_content(),
                },
            )
            return None

        shutdown_period_1: str | None = None
        shutdown_period_2: str | None = None
        shutdown_street: str | None = None
        for info_tag in info_tags:
            info_text: str = info_tag.text.lower()
            if "начало" in info_tag.text.lower():
                shutdown_period_1 = info_tag.tail.strip()
            elif "окончание" in info_tag.text.lower():
                shutdown_period_2 = info_tag.tail.strip()
            elif "адрес" in info_text:
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
