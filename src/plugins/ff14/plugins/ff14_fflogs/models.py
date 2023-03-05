from nonebot_plugin_datastore import get_plugin_data
from pydantic import BaseModel, Field
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

Model = get_plugin_data().Model


class User(Model):
    __table_args__ = (UniqueConstraint("platform", "user_id", name="unique-user"),)

    id: Mapped[int] = mapped_column(primary_key=True)

    platform: Mapped[str]
    user_id: Mapped[str]
    character_name: Mapped[str]
    server_name: Mapped[str]


class BossInfo(BaseModel):
    """BOSS 的信息"""

    name: str
    nicknames: list[str]
    zone: int
    encounter: int
    difficulty: int


class JobInfo(BaseModel):
    """职业的信息"""

    name: str
    nicknames: list[str]
    spec: int


class FFlogsDataModel(BaseModel):
    version: str
    boss: list[BossInfo]
    job: list[JobInfo]


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
    area: int | None = None
    default: bool | None = None
    filtered_name: str | None = None


class Zones(BaseModel):
    id: int
    name: str
    frozen: bool
    encounters: list[Encounter]
    brackets: Brackets
    partitions: list[Partition] | None = None


class Spec(BaseModel):
    id: int
    name: str


class Class(BaseModel):
    id: int
    name: str
    specs: list[Spec]


class Ranking(BaseModel):
    name: str
    class_: int = Field(..., alias="class")
    spec: int
    total: float
    duration: int
    startTime: int
    fightID: int
    reportID: str
    guildName: str | None
    serverName: str
    regionName: str
    hidden: bool
    patch: float
    aDPS: float
    rDPS: float
    nDPS: float
    pDPS: float
    rank: int


class FFLogsRanking(BaseModel):
    page: int
    hasMorePages: bool
    count: int
    rankings: list[Ranking]


class CharacterRanking(BaseModel):
    encounterID: int
    encounterName: str
    class_: str = Field(..., alias="class")
    spec: str
    rank: int
    outOf: int
    duration: int
    startTime: int
    reportID: str
    fightID: int
    difficulty: int
    size: int
    characterID: int
    characterName: str
    server: str
    percentile: float
    ilvlKeyOrPatch: float
    total: float
    estimated: bool
