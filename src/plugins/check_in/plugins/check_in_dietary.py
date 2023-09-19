from nonebot.params import Arg, Depends
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.typing import T_State

from src.plugins.user import UserSession
from src.utils.annotated import AsyncSession, PlainTextArgs
from src.utils.helpers import parse_str

from .. import check_in
from ..models import DietaryRecord

__plugin_meta__ = PluginMetadata(
    name="饮食打卡",
    description="记录饮食是否健康",
    usage="""记录饮食是否健康
/饮食打卡""",
    supported_adapters=inherit_supported_adapters("user"),
)
dietary_cmd = check_in.command("dietary", aliases={"饮食打卡"})


@dietary_cmd.handle()
async def handle_first_message(state: T_State, content: PlainTextArgs):
    state["content"] = content


@dietary_cmd.got(
    "content",
    prompt="今天你吃的怎么样呢？请输入 A 或 B（A：健康饮食少油少糖 B：我摆了偷吃了炸鸡奶茶）",
    parameterless=[Depends(parse_str("content"))],
)
async def _(
    session: AsyncSession,
    user: UserSession,
    content: str = Arg(),
):
    content = content.lower()
    if not content:
        await dietary_cmd.reject("饮食情况不能为空，请重新输入", at_sender=True)

    if content not in ("a", "b"):
        await dietary_cmd.reject("饮食情况只能输入 A 或 B 哦，请重新输入", at_sender=True)

    healthy = content == "a"
    session.add(DietaryRecord(user_id=user.uid, healthy=healthy))
    await session.commit()

    if healthy:
        await dietary_cmd.finish("已成功记录，你真棒哦！祝你早日瘦成一道闪电～", at_sender=True)
    else:
        await dietary_cmd.finish("摸摸你的小肚子，下次不可以再这样了哦～", at_sender=True)
