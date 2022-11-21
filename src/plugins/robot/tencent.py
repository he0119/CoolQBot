""" 腾讯机器人

自然语言处理
https://console.cloud.tencent.com/nlp
闲聊 功能
https://cloud.tencent.com/document/api/271/39416
"""
import json
from typing import Optional

from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.nlp.v20190408 import models, nlp_client

from .config import global_config, plugin_config


async def call_tencent_api(text: str) -> str | None:
    """调用腾讯机器人的 API 获取回复"""
    cred = credential.Credential(
        plugin_config.tencent_ai_secret_id,
        plugin_config.tencent_ai_secret_key,
    )
    httpProfile = HttpProfile(endpoint="nlp.tencentcloudapi.com")

    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = nlp_client.NlpClient(cred, "ap-guangzhou", clientProfile)

    req = models.ChatBotRequest()
    params = {"Query": text}
    req.from_json_string(json.dumps(params))

    resp = client.ChatBot(req)
    if resp.Reply:
        msg: str = resp.Reply
        # 替换腾讯昵称
        # 从小龙女换成设置的机器人昵称
        nickname: str = list(global_config.nickname)[0]
        msg = msg.replace("腾讯小龙女", nickname)
        msg = msg.replace("小龙女", nickname)

        return msg
