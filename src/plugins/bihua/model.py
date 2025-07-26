from datetime import datetime
from pathlib import Path

from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column

from .utils import get_image_path


class Bihua(Model):
    """壁画模型"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]  # 收藏者用户 ID
    session_id: Mapped[str]  # 群组 ID
    name: Mapped[str]  # 壁画名称
    image_hash: Mapped[str]  # 图片 hash 值，用于去重
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)  # 创建时间

    def image_path(self) -> Path:
        """获取壁画图片的本地存储路径"""
        return get_image_path(self.session_id, self.image_hash)
