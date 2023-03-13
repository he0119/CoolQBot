from nonebot.params import Arg, Depends
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
from nonebot_plugin_datastore import get_session
from sqlalchemy.ext.asyncio import AsyncSession

from src.utils.helpers import (
    GroupOrChannel,
    get_group_or_channel,
    get_plaintext_content,
    parse_str,
)

from .. import check_in
from ..helpers import ensure_user
from ..models import WeightRecord

__plugin_meta__ = PluginMetadata(
    name="体重打卡",
    description="设置和查看目标体重并记录体重",
    usage="""查看目标体重
/目标体重
设置目标体重
/目标体重 60
记录体重
/记录体重""",
    extra={
        "adapters": ["OneBot V11", "OneBot V12"],
    },
)
target_weight_cmd = check_in.command("weight", aliases={"目标体重"})


@target_weight_cmd.handle()
async def _(
    state: T_State,
    content: str | None = Depends(get_plaintext_content),
    group_or_channel: GroupOrChannel = Depends(get_group_or_channel),
    session: AsyncSession = Depends(get_session),
):
    if content:
        state["content"] = content
    else:
        user = await ensure_user(session, group_or_channel)
        if user.target_weight:
            await target_weight_cmd.finish(
                f"你的目标体重是 {user.target_weight}kg，继续努力哦～", at_sender=True
            )


@target_weight_cmd.got(
    "content", prompt="请输入你的目标体重哦～", parameterless=[Depends(parse_str("content"))]
)
async def _(
    content: str = Arg(),
    group_or_channel: GroupOrChannel = Depends(get_group_or_channel),
    session: AsyncSession = Depends(get_session),
):
    content = content.strip()
    if not content:
        await target_weight_cmd.reject("目标体重不能为空，请重新输入", at_sender=True)

    try:
        weight = float(content)
    except ValueError:
        await target_weight_cmd.reject("目标体重只能输入数字哦，请重新输入", at_sender=True)

    if weight <= 0:
        await target_weight_cmd.reject("目标体重必须大于 0kg，请重新输入", at_sender=True)

    user = await ensure_user(session, group_or_channel)
    user.target_weight = weight
    await session.commit()

    await target_weight_cmd.finish("已成功设置，你真棒哦！祝你早日达成目标～", at_sender=True)


weight_record_cmd = check_in.command("weight_record", aliases={"记录体重"})


@weight_record_cmd.handle()
async def _(
    state: T_State,
    content: str = Depends(get_plaintext_content),
):
    state["content"] = content


@weight_record_cmd.got(
    "content", prompt="今天你的体重是多少呢？", parameterless=[Depends(parse_str("content"))]
)
async def _(
    content: str = Arg(),
    group_or_channel: GroupOrChannel = Depends(get_group_or_channel),
    session: AsyncSession = Depends(get_session),
):
    content = content.strip()
    if not content:
        await target_weight_cmd.reject("体重不能为空，请重新输入", at_sender=True)

    try:
        weight = float(content)
    except ValueError:
        await target_weight_cmd.reject("体重只能输入数字哦，请重新输入", at_sender=True)

    if weight <= 0:
        await target_weight_cmd.reject("目标体重必须大于 0kg，请重新输入", at_sender=True)

    user = await ensure_user(session, group_or_channel)

    session.add(WeightRecord(user=user, weight=weight))
    await session.commit()

    await weight_record_cmd.finish("已成功记录，你真棒哦！祝你早日瘦成一道闪电～", at_sender=True)
