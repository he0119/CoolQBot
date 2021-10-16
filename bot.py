from pathlib import Path

import nonebot
from nonebot.adapters.cqhttp import Bot as CQHTTPBot
from nonebot.log import default_format, logger

nonebot.init()
app = nonebot.get_asgi()

driver = nonebot.get_driver()
driver.register_adapter("cqhttp", CQHTTPBot)

# 添加额外的配置
config = nonebot.get_driver().config
config.home_dir_path = Path().resolve()
# 插件数据目录
config.data_dir_path = config.home_dir_path / "data"

# 自定义 logger
logger.add(
    config.data_dir_path / "logs" / "error.log",
    rotation="5 MB",
    diagnose=False,
    level="ERROR",
    format=default_format,
)

# 加载外部插件
nonebot.load_plugin("nonebot_plugin_sentry")
# 加载开发环境插件
if config.debug:
    nonebot.load_plugin("nonebot_plugin_test")
    nonebot.load_plugin("nonebot_plugin_docs")
# 加载自己的插件
nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    logger.warning("Always use `nb run` to start the bot instead of manually running!")
    nonebot.run(app="__mp_main__:app")
