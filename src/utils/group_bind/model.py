from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column


class GroupBind(Model):
    """群组绑定模型"""

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str]
    """群组 ID"""
    bind_id: Mapped[str]
    """当前绑定的群组 ID"""
