"""QQ 机器人

机器人平台校验文件
"""

import nonebot
from fastapi import FastAPI, Request
from nonebot.adapters.qq import Adapter

app: FastAPI = nonebot.get_app()
adapter = nonebot.get_adapter(Adapter)


# /bot_id.json
# {"bot_appid": "bot_id"}
async def check_qq(request: Request):
    url = request.url.path
    bot_id = url.removeprefix("/").removesuffix(".json")
    return {"bot_appid": int(bot_id)}


# 仅注册配置中的 QQ 机器人
for bot in adapter.qq_config.qq_bots:
    app.get(f"/{bot.id}.json")(check_qq)
