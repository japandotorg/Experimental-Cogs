import asyncio
import datetime
import pydantic
from typing import Annotated, Dict, Generic, Optional, TypeAlias, TypeVar

from .utils import LONDON, ClockType, timezone


T = TypeVar("T")


LondonDateTime: TypeAlias = Annotated[
    pydantic.AwareDatetime,
    pydantic.BeforeValidator(
        lambda d: datetime.datetime.fromtimestamp(d).astimezone(LONDON)
        if isinstance(d, (int, float))
        else d
    ),
    pydantic.AfterValidator(timezone),
    pydantic.PlainSerializer(lambda d: d.timestamp(), return_type=float),
]


class Model(pydantic.BaseModel, Generic[T]):
    model_config: pydantic.ConfigDict = pydantic.ConfigDict(
        arbitrary_types_allowed=True, strict=True
    )

    async def to_json(self) -> Dict[str, T]:
        return await asyncio.to_thread(lambda: self.model_dump(mode="python"))


class Clock(Model[ClockType]):
    start: LondonDateTime = pydantic.Field(
        default_factory=lambda: datetime.datetime.now(LONDON)
    )
    end: Optional[LondonDateTime] = pydantic.Field(default=None)
