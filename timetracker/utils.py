import pytz
import datetime
from typing import Final, Optional, TypedDict


MAXIMUM_ROLES: Final[int] = 10


LONDON: pytz.tzinfo.BaseTzInfo = pytz.timezone("Europe/London")


def timezone(dt: datetime.datetime) -> datetime.datetime:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("datetime object must be timezone aware.")
    if getattr(dt.tzinfo, "zone", None) != "Europe/London":
        try:
            dt: datetime.datetime = dt.astimezone(LONDON)
        except Exception as error:
            raise ValueError(
                "could not convert datetime to Europe/London timezone: {}".format(
                    error
                )
            )
    if getattr(dt.tzinfo, "zone", "UTC") != "Europe/London":
        raise ValueError(
            "datetime object must be Europe/London timezone after conversion."
        )
    return dt


class ClockType(TypedDict):
    start: float
    end: Optional[float]
