"""随机美食推荐插件。"""

import re

from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import Alconna, Args, CommandMeta, Image, MultiVar, Text, on_alconna

from .data_source import recommend_food
from .image_api import get_food_image

__plugin_meta__ = PluginMetadata(
    name="吃什么",
    description="随机推荐一种美食",
    usage="""随机推荐一种美食
吃什么
吃啥？
今晚吃什么
今天 中午吃啥？""",
    supported_adapters=inherit_supported_adapters("nonebot_plugin_alconna"),
)

what_to_eat_cmd = on_alconna(
    Alconna(
        "吃什么",
        Args["context?#场景", MultiVar(str, flag="+")],
        meta=CommandMeta(
            description=__plugin_meta__.description,
            example=__plugin_meta__.usage,
        ),
    ),
    use_cmd_start=False,
    block=True,
)

what_to_eat_cmd.shortcut(
    re.compile(r"(?P<context>.*?)吃(?:啥|什么)[?？]?"),
    arguments=["{context}"],
    fuzzy=False,
    compact=False,
    humanized="xxxx吃啥 / xxxx吃什么",
)


@what_to_eat_cmd.handle()
async def what_to_eat_handle():
    food = recommend_food()
    text = f"推荐你吃：{food.name}！"
    image = await get_food_image(food.commons_file)
    if not image:
        await what_to_eat_cmd.finish(text, at_sender=True)

    message = Text(f"{text}\n") + Image(raw=image.content, mimetype=image.mimetype)
    message += Text(f"\n{image.attribution}")
    await what_to_eat_cmd.finish(message, at_sender=True)
