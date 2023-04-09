from nonebot.params import Arg, Depends
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from src.utils.helpers import UserInfo, get_plaintext_content, get_user_info, parse_str
from src.utils.typing import AsyncSession

from .. import check_in
from ..helpers import ensure_user
from ..models import BodyFatRecord

__plugin_meta__ = PluginMetadata(
    name="体脂打卡",
    description="设置和查看目标体脂并记录体脂",
    usage="""查看目标体脂
/目标体脂
设置目标体脂
/目标体脂 20
记录体脂
/体脂打卡
/体制打卡 20""",
    extra={
        "adapters": ["OneBot V11", "OneBot V12"],
    },
)

target_body_fat_cmd = check_in.command("body_fat", aliases={"目标体脂"})


@target_body_fat_cmd.handle()
async def handle_first_message(
    state: T_State,
    session: AsyncSession,
    content: str | None = Depends(get_plaintext_content),
    user_info: UserInfo = Depends(get_user_info),
):
    """目标体脂"""
    if content:
        state["content"] = content
    else:
        user = await ensure_user(session, user_info)
        if user.target_body_fat:
            await target_body_fat_cmd.finish(
                f"你的目标体脂是 {user.target_body_fat}%，继续努力哦～", at_sender=True
            )


@target_body_fat_cmd.got(
    "content", prompt="请输入你的目标体脂哦～", parameterless=[Depends(parse_str("content"))]
)
async def _(
    session: AsyncSession,
    content: str = Arg(),
    user_info: UserInfo = Depends(get_user_info),
):
    """目标体脂"""
    if not content:
        await target_body_fat_cmd.reject("目标体脂不能为空，请重新输入", at_sender=True)

    try:
        body_fat = float(content)
    except ValueError:
        await target_body_fat_cmd.reject("目标体脂只能输入数字哦，请重新输入", at_sender=True)

    if body_fat < 0 or body_fat > 100:
        await target_body_fat_cmd.reject("目标体脂只能在 0% ~ 100% 之间哦，请重新输入", at_sender=True)

    user = await ensure_user(session, user_info)
    user.target_body_fat = body_fat
    await session.commit()

    await target_body_fat_cmd.finish("已成功设置，你真棒哦！祝你早日达成目标～", at_sender=True)


body_fat_record_cmd = check_in.command("body_record", aliases={"记录体脂", "体脂打卡"})


@body_fat_record_cmd.handle()
async def _(
    state: T_State,
    content: str = Depends(get_plaintext_content),
):
    """记录体脂"""
    state["content"] = content


@body_fat_record_cmd.got(
    "content", prompt="今天你的体脂是多少呢？", parameterless=[Depends(parse_str("content"))]
)
async def _(
    session: AsyncSession,
    content: str = Arg(),
    user_info: UserInfo = Depends(get_user_info),
):
    """记录体脂"""
    if not content:
        await body_fat_record_cmd.reject("体脂不能为空，请重新输入", at_sender=True)

    try:
        body_fat = float(content)
    except ValueError:
        await body_fat_record_cmd.reject("体脂只能输入数字哦，请重新输入", at_sender=True)

    if body_fat < 0 or body_fat > 100:
        await target_body_fat_cmd.reject("目标体脂只能在 0% ~ 100% 之间哦，请重新输入", at_sender=True)

    user = await ensure_user(session, user_info)

    session.add(BodyFatRecord(user=user, body_fat=body_fat))
    await session.commit()

    await body_fat_record_cmd.finish("已成功记录，你真棒哦！祝你早日瘦成一道闪电～", at_sender=True)
