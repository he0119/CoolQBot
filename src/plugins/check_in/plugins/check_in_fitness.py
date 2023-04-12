from nonebot.params import Arg, Depends
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from src.utils.annotated import AsyncSession, PlainTextArgs, UserInfo
from src.utils.helpers import parse_str

from .. import check_in
from ..helpers import ensure_user
from ..models import FitnessRecord

__plugin_meta__ = PluginMetadata(
    name="健身打卡",
    description="记录健身情况",
    usage="""记录健身情况
/健身打卡""",
    extra={
        "adapters": ["OneBot V11", "OneBot V12"],
    },
)
fitness_cmd = check_in.command("fitness", aliases={"健身打卡"})


@fitness_cmd.handle()
async def handle_first_message(state: T_State, content: PlainTextArgs):
    state["content"] = content


@fitness_cmd.got(
    "content", prompt="请问你做了什么运动？", parameterless=[Depends(parse_str("content"))]
)
async def _(
    session: AsyncSession,
    user_info: UserInfo,
    content: str = Arg(),
):
    content = content.strip()
    if not content:
        await fitness_cmd.reject("健身内容不能为空，请重新输入", at_sender=True)

    user = await ensure_user(session, user_info)

    session.add(FitnessRecord(user=user, message=content))
    await session.commit()

    await fitness_cmd.finish("已成功记录，你真棒哦！祝你早日瘦成一道闪电～", at_sender=True)
