from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna
from nonebot_plugin_alconna.builtins.extensions.discord import DiscordSlashExtension
from nonebot_plugin_alconna.builtins.extensions.telegram import TelegramSlashExtension
from nonebot_plugin_user import UserSession

from src.plugins.check_in.models import DietaryRecord
from src.utils.annotated import AsyncSession

__plugin_meta__ = PluginMetadata(
    name="饮食打卡",
    description="记录饮食是否健康",
    usage="""记录饮食是否健康
/饮食打卡
/饮食打卡 A""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_user", "nonebot_plugin_alconna"),
)

dietary_cmd = on_alconna(
    Alconna(
        "dietary_checkin",
        Args["content?#A：健康饮食少油少糖 B：我摆了偷吃了炸鸡奶茶", str],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={"饮食打卡"},
    use_cmd_start=True,
    block=True,
    extensions=[
        TelegramSlashExtension(),
        DiscordSlashExtension(name_localizations={"zh-CN": "饮食打卡"}),
    ],
)


@dietary_cmd.handle()
async def handle_first_message(content: Match[str]):
    if content.available:
        dietary_cmd.set_path_arg("content", content.result)


@dietary_cmd.got_path(
    "content",
    prompt="今天你吃的怎么样呢？请输入 A 或 B（A：健康饮食少油少糖 B：我摆了偷吃了炸鸡奶茶）",
)
async def _(session: AsyncSession, user: UserSession, content: str):
    content = content.lower()

    if content not in ("a", "b"):
        await dietary_cmd.reject("饮食情况只能输入 A 或 B 哦，请重新输入", at_sender=True)

    healthy = content == "a"
    session.add(DietaryRecord(user_id=user.user_id, healthy=healthy))
    await session.commit()

    if healthy:
        await dietary_cmd.finish("已成功记录，你真棒哦！祝你早日瘦成一道闪电～", at_sender=True)
    else:
        await dietary_cmd.finish("摸摸你的小肚子，下次不可以再这样了哦～", at_sender=True)
