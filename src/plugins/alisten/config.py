from nonebot import get_driver, get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    """alisten 配置"""

    alisten_server_url: str
    alisten_house_id: str
    alisten_house_password: str = ""


global_config = get_driver().config
plugin_config = get_plugin_config(Config)
