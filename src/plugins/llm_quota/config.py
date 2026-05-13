"""大模型额度查询插件配置"""

from nonebot import get_driver, get_plugin_config
from pydantic import BaseModel


class Config(BaseModel):
    llm_quota_api_url: str = "https://ai.long-antares.ts.net/api/quotas"


global_config = get_driver().config
plugin_config = get_plugin_config(Config)
