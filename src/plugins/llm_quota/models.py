"""大模型额度查询数据模型"""

from nonebot_plugin_orm import Model
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class GroupQuotaConfig(Model):
    """群组额度查询配置"""

    __table_args__ = (UniqueConstraint("session_id", name="unique_group_quota_config"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str]
    """群组会话 ID"""
    api_url: Mapped[str]
    """API 地址"""
