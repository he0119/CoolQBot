"""大模型额度查询数据模型"""

from pydantic import BaseModel


class Bucket(BaseModel):
    """额度桶"""

    name: str
    """桶名称"""
    current: int
    """当前剩余额度（单位：token）"""
    capacity: int
    """总容量（单位：token）"""
    rate: str
    """速率限制"""
    models: list[str]
    """关联的模型列表"""
    paused: bool
    """是否暂停"""
    last_updated: str
    """最后更新时间"""


class QuotasResponse(BaseModel):
    """额度查询响应"""

    buckets: list[Bucket]
    """额度桶列表"""
