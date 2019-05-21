""" Bot
"""
import platform
from pathlib import Path

from aiocqhttp import CQHttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import Config
from .logger import init_logger
from .plugin import PluginManager

class CoolQBot(CQHttp):
    def __init__(self,
                 api_root=None,
                 access_token=None,
                 secret=None,
                 enable_http_post=True,
                 message_class=None,
                 *args,
                 **kwargs):
        super().__init__(api_root=api_root,
                         access_token=access_token,
                         secret=secret,
                         enable_http_post=enable_http_post,
                         message_class=message_class,
                         *args,
                         **kwargs)

        # 如果在 Docker 中
        if platform.system() == 'Linux':
            config_file_path = Path('/home/user/coolq/bot/bot.ini')
            log_file_path = Path('/home/user/coolq/bot/bot.log')
            data_dir_path = Path('/home/user/coolq/bot/data')
            plugins_dir_path = Path('/home/user/coolqbot/plugins')
        else:
            config_file_path = Path('bot/bot.ini')
            log_file_path = Path('bot/bot.log')
            data_dir_path = Path('bot/data')
            plugins_dir_path = Path('plugins')

        default_config = {
            'GROUP_ID': None,
            'IS_COOLQ_PRO': False,
            'ADMIN': None,
            'DEBUG': False,
            'PLUGINS_DIR_PATH': plugins_dir_path,
            'CONFIG_FILE_PATH': config_file_path,
            'LOG_FILE_PATH': log_file_path,
            'DATA_DIR_PATH': data_dir_path
        }

        # 机器人的配置信息
        self.config = Config(default_config)

        # 任务调度
        self.scheduler = AsyncIOScheduler()

        # 插件管理器
        self.plugin_manager = PluginManager(self)

    def init_bot(self):
        if bot.config['CONFIG_FILE_PATH'].exists():
            bot.config.from_file(bot.config['CONFIG_FILE_PATH'])

        init_logger(self)
        bot.logger.debug('Initializing...')

        self.plugin_manager.load_plugin()
        self.plugin_manager.enable_all()
        self.scheduler.start()

        bot.run(host='127.0.0.1', port=8080)


bot = CoolQBot(enable_http_post=False)
