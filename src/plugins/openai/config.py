"""配置文件"""

from nonebot import get_driver, get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    openai_enabled_groups: list[str] = []
    """ 插件启用的群组 """
    openai_api_key: str | None = None
    """ OpenAI 的 API Key """
    openai_model: str = "gpt-4o"
    """ OpenAI 的模型 """
    openai_proxy: str | None = None
    """ OpenAI 的代理地址 """


global_config = get_driver().config
plugin_config = get_plugin_config(Config)
