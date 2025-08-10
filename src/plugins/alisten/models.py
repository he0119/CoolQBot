from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column


class AlistenConfig(Model):
    """alisten 配置模型"""

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str] = mapped_column(unique=True)
    """群组会话 ID"""
    server_url: Mapped[str]
    """alisten 服务器地址"""
    house_id: Mapped[str]
    """房间 ID"""
    house_password: Mapped[str] = mapped_column(default="")
    """房间密码"""
