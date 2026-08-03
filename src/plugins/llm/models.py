"""大模型插件数据模型"""

from nonebot_plugin_orm import Model
from sqlalchemy import JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class GroupLLMConfig(Model):
    """群组大模型配置"""

    __table_args__ = (UniqueConstraint("session_id", name="unique_group_llm_config"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[str]
    """群组会话 ID"""
    model_name: Mapped[str | None] = mapped_column(default=None)
    """默认模型名，为空时使用本群开放的第一个模型"""
    available_models: Mapped[list[str] | None] = mapped_column(JSON(none_as_null=True), default=None)
    """本群可用模型名；为空时不允许使用任何模型"""
    zssm_model: Mapped[str | None] = mapped_column(default=None)
    """“这是什么”解释模型名，为空时跟随本群默认模型"""
    zssm_vision_model: Mapped[str | None] = mapped_column(default=None)
    """“这是什么”视觉模型名"""
    tts_model: Mapped[str | None] = mapped_column(default=None)
    """默认 TTS 模型名"""
