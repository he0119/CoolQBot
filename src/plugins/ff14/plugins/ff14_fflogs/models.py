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
    """副本难度

    绝本的难度是 100

    零式副本的难度是 101，普通和极神是 100
    """
    partition: int | None = None
    """FFLogs 排行榜分区，绝本使用该字段区分不同版本。"""
    version: str | None = None
    partition_end: int | None = None
    """分区结束时间，Unix 时间戳（秒）。"""
    partition_frozen: bool = False


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
    id: int | None = None
    name: str
    compact: str
    area: int | None = None
    default: bool | None = None
    filtered_name: str | None = None
    patch: str | None = None
    partition_type: str | None = Field(default=None, alias="partitionType")
    start_time: int | None = Field(default=None, alias="startTime")
    end_time: int | None = Field(default=None, alias="endTime")
    frozen: bool | None = None


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
    rank: int | None = None


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

    绝本的难度是 100

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
