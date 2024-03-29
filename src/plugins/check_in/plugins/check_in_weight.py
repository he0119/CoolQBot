from nonebot.params import Arg, Depends
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.typing import T_State
from nonebot_plugin_user import UserSession

from src.plugins.check_in import check_in
from src.plugins.check_in.models import WeightRecord
from src.plugins.check_in.utils import get_or_create_user_info
from src.utils.annotated import AsyncSession, OptionalPlainTextArgs, PlainTextArgs
from src.utils.helpers import parse_str

__plugin_meta__ = PluginMetadata(
    name="体重打卡",
    description="设置和查看目标体重并记录体重",
    usage="""查看目标体重
/目标体重
设置目标体重
/目标体重 60
记录体重
/体重打卡
/体重打卡 60""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_user"),
)
target_weight_cmd = check_in.command("weight", aliases={"目标体重"})


@target_weight_cmd.handle()
async def _(
    state: T_State,
    session: AsyncSession,
    user: UserSession,
    content: OptionalPlainTextArgs,
):
    if content:
        state["content"] = content
    else:
        user_info = await get_or_create_user_info(user, session)
        if user_info.target_weight:
            await target_weight_cmd.finish(
                f"你的目标体重是 {user_info.target_weight}kg，继续努力哦～",
                at_sender=True,
            )


@target_weight_cmd.got(
    "content",
    prompt="请输入你的目标体重哦～",
    parameterless=[Depends(parse_str("content"))],
)
async def _(
    session: AsyncSession,
    user: UserSession,
    content: str = Arg(),
):
    content = content.strip()
    if not content:
        await target_weight_cmd.reject("目标体重不能为空，请重新输入", at_sender=True)

    try:
        weight = float(content)
    except ValueError:
        await target_weight_cmd.reject(
            "目标体重只能输入数字哦，请重新输入", at_sender=True
        )

    if weight <= 0:
        await target_weight_cmd.reject(
            "目标体重必须大于 0kg，请重新输入", at_sender=True
        )

    user_info = await get_or_create_user_info(user, session)
    user_info.target_weight = weight
    await session.commit()

    await target_weight_cmd.finish(
        "已成功设置，你真棒哦！祝你早日达成目标～", at_sender=True
    )


weight_record_cmd = check_in.command("weight_record", aliases={"记录体重", "体重打卡"})


@weight_record_cmd.handle()
async def _(state: T_State, content: PlainTextArgs):
    state["content"] = content


@weight_record_cmd.got(
    "content",
    prompt="今天你的体重是多少呢？",
    parameterless=[Depends(parse_str("content"))],
)
async def _(
    session: AsyncSession,
    user: UserSession,
    content: str = Arg(),
):
    content = content.strip()
    if not content:
        await target_weight_cmd.reject("体重不能为空，请重新输入", at_sender=True)

    try:
        weight = float(content)
    except ValueError:
        await target_weight_cmd.reject("体重只能输入数字哦，请重新输入", at_sender=True)

    if weight <= 0:
        await target_weight_cmd.reject(
            "目标体重必须大于 0kg，请重新输入", at_sender=True
        )

    session.add(WeightRecord(user_id=user.user_id, weight=weight))
    await session.commit()

    await weight_record_cmd.finish(
        "已成功记录，你真棒哦！祝你早日瘦成一道闪电～", at_sender=True
    )
