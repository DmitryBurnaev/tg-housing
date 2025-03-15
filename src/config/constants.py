import enum


class SupportedCity(enum.StrEnum):
    """Enumeration of cities supported by the utility notification system."""

    SPB = "SPB"
    RND = "RND"


class SupportedService(enum.StrEnum):
    """Enumeration of utility services that can be monitored for maintenance schedules."""

    ELECTRICITY = "ELECTRICITY"
    COLD_WATER = "COLD_WATER"
    HOT_WATER = "HOT_WATER"

    @classmethod
    def members(cls) -> list["SupportedService"]:
        """Return a list of all supported utility services."""
        return [cls.ELECTRICITY, cls.HOT_WATER, cls.COLD_WATER]


RESOURCE_URLS = {
    SupportedCity.SPB: {
        SupportedService.ELECTRICITY: (
            "https://rosseti-lenenergo.ru/planned_work/?"
            "city={city}&date_start={date_start}&date_finish={date_finish}&street={street_name}"
        ),
        SupportedService.HOT_WATER: (
            "https://aotek.spb.ru/grafik/?street={street_name}+{street_prefix}&house={house}"
        ),
        SupportedService.COLD_WATER: "https://www.vodokanal.spb.ru/presscentr/remontnye_raboty/",
    }
}
CITY_NAME_MAP = {
    SupportedCity.SPB: "Санкт-Петербург",
}
