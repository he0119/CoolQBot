from nonebot_plugin_orm import Model
from pydantic import BaseModel, Field
from sqlalchemy.orm import Mapped, mapped_column


class User(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(index=True, unique=True)
    character_name: Mapped[str]
    server_name: Mapped[str]


class BossInfo(BaseModel):
    """BOSS 的信息"""

    name: str
    nicknames: list[str]
    zone: int
    encounter: int
    difficulty: int
    """副本难度难度

    绝本的难度是 101

    零式副本的难度是 101，普通的则是 100

    极神也是 100
    """


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
    """副本难度难度

    绝本的难度是 101

    零式副本的难度是 101，普通的则是 100

    极神也是 100
    """
    size: int
    characterID: int
    characterName: str
    server: str
    percentile: float
    ilvlKeyOrPatch: float
    total: float
