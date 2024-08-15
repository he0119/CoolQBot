from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Match, on_alconna
from nonebot_plugin_user import UserSession

from src.plugins.check_in.models import FitnessRecord
from src.utils.annotated import AsyncSession

__plugin_meta__ = PluginMetadata(
    name="健身打卡",
    description="记录健身情况",
    usage="""记录健身情况
/健身打卡
/健身打卡 跑步 30 分钟""",
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_user", "nonebot_plugin_alconna"
    ),
)

fitness_cmd = on_alconna(
    Alconna(
        "健身打卡",
        Args["content?#健身内容", str],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    aliases={("check_in.fitness")},
    use_cmd_start=True,
    block=True,
)


@fitness_cmd.handle()
async def handle_first_message(content: Match[str]):
    if content.available:
        fitness_cmd.set_path_arg("content", content.result)


@fitness_cmd.got_path("content", prompt="请问你做了什么运动？")
async def _(
    session: AsyncSession,
    user: UserSession,
    content: str,
):
    session.add(FitnessRecord(user_id=user.user_id, message=content))
    await session.commit()

    await fitness_cmd.finish(
        "已成功记录，你真棒哦！祝你早日瘦成一道闪电～", at_sender=True
    )
