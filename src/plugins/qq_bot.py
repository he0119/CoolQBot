"""QQ 机器人

机器人平台校验文件
"""

import nonebot
from fastapi import FastAPI, Request
from nonebot import logger
from nonebot.adapters.qq import Adapter


# /bot_id.json
# {"bot_appid": "bot_id"}
async def check_qq(request: Request):
    url = request.url.path
    bot_id = url.removeprefix("/").removesuffix(".json")
    return {"bot_appid": int(bot_id)}


try:
    app: FastAPI = nonebot.get_app()
    adapter = nonebot.get_adapter(Adapter)
    # 仅注册配置中的 QQ 机器人
    for bot in adapter.qq_config.qq_bots:
        app.get(f"/{bot.id}.json")(check_qq)
except ValueError:
    logger.warning("未找到 QQ 机器人配置，跳过注册 /bot_id.json 路由")
