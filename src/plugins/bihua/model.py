from datetime import datetime

from nonebot_plugin_orm import Model
from sqlalchemy.orm import Mapped, mapped_column


class Bihua(Model):
    """壁画模型"""

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]  # 收藏者用户ID
    group_id: Mapped[str]  # 群组ID
    name: Mapped[str]  # 壁画名称
    image_hash: Mapped[str]  # 图片hash值，用于去重
    image_url: Mapped[str | None]  # 图片URL（如果有）
    image_data: Mapped[bytes | None]  # 图片数据（如果需要本地存储）
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)  # 创建时间
