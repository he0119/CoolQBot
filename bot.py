import nonebot
from nonebot.adapters.discord import Adapter as DiscordAdapter
from nonebot.adapters.dodo import Adapter as DodoAdapter
from nonebot.adapters.feishu import Adapter as FeishuAdapter
from nonebot.adapters.kaiheila import Adapter as KaiheilaAdapter
from nonebot.adapters.onebot.v11 import Adapter as OneBotV11Adapter
from nonebot.adapters.onebot.v12 import Adapter as OneBotV12Adapter
from nonebot.adapters.qq import Adapter as QQAdapter
from nonebot.adapters.red import Adapter as RedAdapter
from nonebot.adapters.satori import Adapter as SatoriAdapter
from nonebot.adapters.telegram import Adapter as TelegramAdapter
from nonebot.log import logger
from sqlalchemy import StaticPool

nonebot.init(sqlalchemy_engine_options={"poolclass": StaticPool})
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter(DiscordAdapter)
driver.register_adapter(DodoAdapter)
driver.register_adapter(FeishuAdapter)
driver.register_adapter(KaiheilaAdapter)
driver.register_adapter(OneBotV11Adapter)
driver.register_adapter(OneBotV12Adapter)
driver.register_adapter(QQAdapter)
driver.register_adapter(RedAdapter)
driver.register_adapter(SatoriAdapter)
driver.register_adapter(TelegramAdapter)

# 替换内置权限
from src.utils.permission import patch_permission

patch_permission()

# 替换用户
from src.utils.user import patch_user

patch_user()

# 加载插件
nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    logger.warning("Always use `nb run` to start the bot instead of manually running!")
    nonebot.run(app="__mp_main__:app")
