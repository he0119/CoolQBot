from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession

from src.plugins.check_in.models import WeightRecord
from src.plugins.check_in.utils import get_or_create_user_info
from src.utils.annotated import AsyncSession

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
    supported_adapters=inherit_supported_adapters("nonebot_plugin_user", "nonebot_plugin_alconna"),
)

target_weight_cmd = on_alconna(
    Alconna(
        "target-weight",
        Args["target?#目标体重", str],
        meta=CommandMeta(
            description="设置和查看目标体重",
            example="查看目标体重\n/目标体重\n设置目标体重\n/目标体重 60",
        ),
    ),
    aliases={"目标体重"},
    use_cmd_start=True,
    block=True,
    extensions=[TelegramSlashExtension(), DiscordSlashExtension(name_localizations={"zh-CN": "目标体重"})],
)


@target_weight_cmd.handle()
async def _(session: AsyncSession, user: UserSession, target: Match[str]):
    if target.available:
        target_weight_cmd.set_path_arg("target", target.result)
    else:
        user_info = await get_or_create_user_info(user, session)
        if user_info.target_weight:
            await target_weight_cmd.finish(
                f"你的目标体重是 {user_info.target_weight}kg，继续努力哦～",
                at_sender=True,
            )


@target_weight_cmd.got_path("target", prompt="请输入你的目标体重哦～")
async def _(session: AsyncSession, user: UserSession, target: str):
    target = target.strip()
    if not target:
        await target_weight_cmd.reject("目标体重不能为空，请重新输入", at_sender=True)

    try:
        weight = float(target)
    except ValueError:
        await target_weight_cmd.reject("目标体重只能输入数字哦，请重新输入", at_sender=True)

    if weight <= 0:
        await target_weight_cmd.reject("目标体重必须大于 0kg，请重新输入", at_sender=True)

    user_info = await get_or_create_user_info(user, session)
    user_info.target_weight = weight
    await session.commit()

    await target_weight_cmd.finish("已成功设置，你真棒哦！祝你早日达成目标～", at_sender=True)


weight_record_cmd = on_alconna(
    Alconna(
        "weight_checkin",
        Args["content?#体重（kg）", str],
        meta=CommandMeta(
            description="记录体重",
            example="记录体重\n/体重打卡\n/体重打卡 60",
        ),
    ),
    aliases={"体重打卡", "记录体重"},
    use_cmd_start=True,
    block=True,
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "体重打卡"}),
    ],
)


@weight_record_cmd.handle()
async def _(content: Match[str]):
    if content.available:
        weight_record_cmd.set_path_arg("content", content.result)


@weight_record_cmd.got_path("content", prompt="今天你的体重是多少呢？")
async def _(session: AsyncSession, user: UserSession, content: str):
    try:
        weight = float(content)
    except ValueError:
        await target_weight_cmd.reject("体重只能输入数字哦，请重新输入", at_sender=True)

    if weight <= 0:
        await target_weight_cmd.reject("目标体重必须大于 0kg，请重新输入", at_sender=True)

    session.add(WeightRecord(user_id=user.user_id, weight=weight))
    await session.commit()

    await weight_record_cmd.finish("已成功记录，你真棒哦！祝你早日瘦成一道闪电～", at_sender=True)
