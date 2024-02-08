from nonebot.params import Arg, Depends
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.typing import T_State
from nonebot_plugin_user import UserSession

from src.plugins.check_in import check_in
from src.plugins.check_in.models import FitnessRecord
from src.utils.annotated import AsyncSession, PlainTextArgs
from src.utils.helpers import parse_str

__plugin_meta__ = PluginMetadata(
    name="健身打卡",
    description="记录健身情况",
    usage="""记录健身情况
/健身打卡""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_user"),
)
fitness_cmd = check_in.command("fitness", aliases={"健身打卡"})


@fitness_cmd.handle()
async def handle_first_message(state: T_State, content: PlainTextArgs):
    state["content"] = content


@fitness_cmd.got(
    "content",
    prompt="请问你做了什么运动？",
    parameterless=[Depends(parse_str("content"))],
)
async def _(
    session: AsyncSession,
    user: UserSession,
    content: str = Arg(),
):
    content = content.strip()
    if not content:
        await fitness_cmd.reject("健身内容不能为空，请重新输入", at_sender=True)

    session.add(FitnessRecord(user_id=user.user_id, message=content))
    await session.commit()

    await fitness_cmd.finish(
        "已成功记录，你真棒哦！祝你早日瘦成一道闪电～", at_sender=True
    )
