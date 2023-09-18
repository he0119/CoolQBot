from dataclasses import dataclass
from datetime import datetime

from nonebot_plugin_datastore import get_plugin_data
from nonebot_plugin_session import Session, SessionIdType, SessionLevel
from nonebot_plugin_userinfo import UserInfo
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

plugin_data = get_plugin_data()
plugin_data.use_global_registry()

Model = plugin_data.Model


class User(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    binds: Mapped[list["Bind"]] = relationship(back_populates="auser")
    """当前绑定的平台"""
    bind: Mapped["Bind"] = relationship(back_populates="buser")
    """初始时绑定的平台"""


class Bind(Model):
    pid: Mapped[str] = mapped_column(String(64), primary_key=True)
    """平台 ID"""
    platform: Mapped[str] = mapped_column(String(32), primary_key=True)
    """平台名称"""
    aid: Mapped[int] = mapped_column(ForeignKey("user_user.id"))
    """当前绑定的账号 ID"""
    bid: Mapped[int] = mapped_column(ForeignKey("user_user.id"))
    """初始时绑定的账号 ID"""
    auser: Mapped[User] = relationship(back_populates="binds", foreign_keys=[aid])
    """当前绑定的账号"""
    buser: Mapped[User] = relationship(back_populates="bind", foreign_keys=[bid])
    """初始时绑定的账号"""


User.binds = relationship(
    Bind, uselist=True, back_populates="auser", foreign_keys=[Bind.aid]
)
User.bind = relationship(Bind, back_populates="buser", foreign_keys=[Bind.bid])


@dataclass
class UserSession:
    session: Session
    info: UserInfo | None
    user: User

    @property
    def uid(self) -> int:
        """用户 ID"""
        return self.user.id

    @property
    def name(self) -> str:
        """用户名"""
        return self.user.name

    @property
    def created_at(self) -> datetime:
        """用户创建日期"""
        return self.user.created_at.astimezone()

    @property
    def pid(self) -> str:
        """用户所在平台 ID"""
        assert self.session.id1
        return self.session.id1

    @property
    def platform(self) -> str:
        """用户所在平台"""
        return self.session.platform

    @property
    def level(self) -> SessionLevel:
        """用户会话级别"""
        return self.session.level

    @property
    def group_id(self) -> str:
        """用户所在群组 ID

        ID 由平台名称和平台的群组 ID 组成，例如 `qq_123456789`。
        """
        return self.session.get_id(
            id_type=SessionIdType.GROUP,
            include_platform=True,
            include_bot_type=False,
            include_bot_id=False,
        )
