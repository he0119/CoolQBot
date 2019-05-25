""" CoolQBot 类
"""
import platform
from pathlib import Path

from aiocqhttp import CQHttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import Config
from .logger import init_logger
from .plugin import Plugin, PluginManager


class CoolQBot(CQHttp):
    # Plugin 类，所有插件都应该是这个类
    Plugin = Plugin

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

        # 根据运行的系统，配置不同的设置
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
            'ADMIN': None,
            'IS_COOLQ_PRO': False,
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

    def run(self, host=None, port=None, *args, **kwargs):
        # 如果机器人配置文件存在则先读取配置
        if self.config['CONFIG_FILE_PATH'].exists():
            self.config.from_file(self.config['CONFIG_FILE_PATH'])

        # 初始化日志
        init_logger(self)
        self.logger.debug('CoolQBot 启动中...')

        # 加载并启用所有的插件
        # TODO: 记录插件的启用/禁用情况，恢复上次记录的状态
        self.plugin_manager.load_plugin()
        self.plugin_manager.enable_all()
        # 启动计划任务
        self.scheduler.start()

        super().run(host=host, port=port, *args, **kwargs)
