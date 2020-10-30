from pathlib import Path

import nonebot

nonebot.init()
app = nonebot.get_asgi()

# 添加额外的配置
config = nonebot.get_driver().config
config.home_dir_path = Path().resolve()
# 插件数据目录
config.data_dir_path = config.home_dir_path / 'data'

# 自定义 logger
from nonebot.log import default_format, logger

logger.add(
    config.data_dir_path / 'logs' / 'error.log',
    rotation='5 MB',
    diagnose=False,
    level='ERROR',
    format=default_format
)

# 加载插件
nonebot.load_plugins('src/plugins')

# 测试框架
try:
    import nonebot_test
    nonebot_test.init()
except:
    pass

if __name__ == '__main__':
    nonebot.run(app='bot:app')
