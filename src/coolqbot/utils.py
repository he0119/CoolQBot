""" 一些工具
"""
from coolqbot.plugin import PluginManager

plugin_manager = PluginManager()


def get_history_pkl_name(dt):
    time_str = dt.strftime('%Y-%m')
    return time_str
