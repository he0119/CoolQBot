from nonebot.adapters import MessageSegment
from pydantic import BaseModel


class MentionedUser(BaseModel):
    """提及的用户信息"""

    id: str
    segment: MessageSegment


class UserInfo(BaseModel, frozen=True):
    """确定一个用户所需的信息"""

    platform: str
    user_id: str


class GroupInfo(BaseModel, frozen=True):
    """确定一个群或频道所需信息"""

    platform: str
    group_id: str
    guild_id: str
    channel_id: str

    @property
    def detail_type(self) -> str:
        """根据是否有 group_id 判断是群还是频道"""
        if self.group_id:
            return "group"
        return "channel"

    @property
    def send_message_args(self) -> dict[str, str]:
        """发送消息所需数据"""
        return {
            "group_id": self.group_id,
            "channel_id": self.channel_id,
            "guild_id": self.guild_id,
        }
