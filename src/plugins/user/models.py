from nonebot_plugin_datastore import get_plugin_data
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

plugin_data = get_plugin_data()
plugin_data.use_global_registry()

Model = plugin_data.Model


class User(Model):
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))

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
