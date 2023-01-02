import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
from nonebot.adapters.onebot.v12 import Adapter as OneBotV12Adapter
from nonebot.log import logger

nonebot.init()
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)
driver.register_adapter(OneBotV12Adapter)

# 加载插件
nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    logger.warning("Always use `nb run` to start the bot instead of manually running!")
    nonebot.run(app="__mp_main__:app")
