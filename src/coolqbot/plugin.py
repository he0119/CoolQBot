import os

from coolqbot.logger import logger


class PluginManager(object):

    def __init__(self):
        self._plugin_prefix = 'plugins'

    def _get_plugin_name(self, name):
        return f'{self._plugin_prefix}.{name}'

    def load_plugin(self):
        for plugin_name in os.listdir('plugins'):
            pathname = os.path.join('plugins', plugin_name)
            if os.path.isfile(pathname):
                plugin_name = plugin_name.split('.')[0]
                try:
                    __import__(self._get_plugin_name(plugin_name))
                    logger.info(f'Plugin [{plugin_name}] loaded.')
                except ImportError:
                    logger.error(
                        f'Import error: can not import [{plugin_name}]'
                    )
