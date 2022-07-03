from typing import Optional

from pydantic import BaseModel


class Encounter(BaseModel):
    id: int
    name: str


class Brackets(BaseModel):
    min: int
    max: float
    bucket: float
    type: str


class Partition(BaseModel):
    name: str
    compact: str
    area: Optional[int] = None
    default: Optional[bool] = None
    filtered_name: Optional[str] = None


class Zones(BaseModel):
    id: int
    name: str
    frozen: bool
    encounters: list[Encounter]
    brackets: Brackets
    partitions: Optional[list[Partition]] = None


class FFLogsZones(BaseModel):
    __root__: list[Zones]

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]


class Spec(BaseModel):
    id: int
    name: str


class Class(BaseModel):
    id: int
    name: str
    specs: list[Spec]


class FFLogsClasses(BaseModel):
    __root__: list[Class]

    def __iter__(self):
        return iter(self.__root__)

    def __getitem__(self, item):
        return self.__root__[item]
