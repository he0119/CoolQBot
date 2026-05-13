"""大模型额度查询数据模型"""

from pydantic import BaseModel


class Bucket(BaseModel):
    name: str
    current: int
    capacity: int
    rate: str
    models: list[str]
    paused: bool
    last_updated: str


class QuotasResponse(BaseModel):
    buckets: list[Bucket]
