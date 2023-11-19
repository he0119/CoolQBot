import nonebot
from nonebot.adapters.kaiheila import Adapter as KaiheilaAdapter
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
from nonebot.adapters.onebot.v12 import Adapter as OneBotV12Adapter
from nonebot.adapters.qq import Adapter as QQAdapter
from nonebot.adapters.qqguild import Adapter as QQGuildAdapter
from nonebot.adapters.red import Adapter as RedAdapter
from nonebot.adapters.satori import Adapter as SatoriAdapter
from nonebot.log import logger
from sqlalchemy import StaticPool

nonebot.init(sqlalchemy_engine_options={"poolclass": StaticPool})
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(OneBotV11Adapter)
driver.register_adapter(OneBotV12Adapter)
driver.register_adapter(KaiheilaAdapter)
driver.register_adapter(QQAdapter)
driver.register_adapter(QQGuildAdapter)
driver.register_adapter(RedAdapter)
driver.register_adapter(SatoriAdapter)

# 加载插件
nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    logger.warning("Always use `nb run` to start the bot instead of manually running!")
    nonebot.run(app="__mp_main__:app")
