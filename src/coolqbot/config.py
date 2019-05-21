""" 配置文件，不同平台设置不同
"""
import configparser


class Config(dict):
    def __init__(self, defaults=None):
        super().__init__(defaults or {})

    def from_object(self, obj):
        """ 从对象中获取配置
        """
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)

    def from_file(self, path):
        """ 从配置文件中获取配置

        `ini` 格式，`bot` 下的值
        """
        # 读取配置文件
        config = configparser.ConfigParser()
        config.read(path)

        if 'bot' not in config:
            return

        for key in config['bot']:
            self[key.upper()] = config['bot'][key]
