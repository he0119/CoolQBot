import os

from coolqbot.bot import bot
from coolqbot.config import PLUGINS_PATH


class PluginManager(object):

    def __init__(self):
        self._plugin_prefix = 'plugins'

    def _get_plugin_name(self, name):
        return f'{self._plugin_prefix}.{name}'

    def load_plugin(self):
        for filename in os.listdir(PLUGINS_PATH):
            pathname = os.path.join(PLUGINS_PATH, filename)
            if os.path.isfile(pathname):
                plugin_name = filename.split('.')[0]
                try:
                    __import__(self._get_plugin_name(plugin_name))
                    bot.logger.info(f'Plugin [{plugin_name}] loaded.')
                except ImportError as e:
                    bot.logger.error(
                        f'Import error: can not import [{plugin_name}], because {e}'
                    )
