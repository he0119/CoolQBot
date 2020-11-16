""" 图灵机器人

http://www.turingapi.com/
"""
import json
from typing import Optional

import httpx
from nonebot.typing import Event

from src.utils.helpers import context_id

from .config import plugin_config


async def call_tuling_api(event: Event, text: str) -> Optional[str]:
    """ 调用图灵机器人的 API 获取回复 """
    if not plugin_config.tuling_api_key:
        return None

    if not text:
        return None

    url = 'http://openapi.tuling123.com/openapi/api/v2'

    # 构造请求数据
    payload = {
        'reqType': 0,
        'perception': {
            'inputText': {
                'text': text
            }
        },
        'userInfo': {
            'apiKey': plugin_config.tuling_api_key,
            'userId': context_id(event, use_hash=True)
        }
    }

    group_unique_id = context_id(event, mode='group', use_hash=True)
    if group_unique_id:
        payload['userInfo']['groupId'] = group_unique_id

    try:
        # 使用 httpx 库发送最终的请求
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                # 如果 HTTP 响应状态码不是 200，说明调用失败
                return None

            resp_payload = json.loads(resp.text)
            if resp_payload['intent']['code'] == 4003:
                # 如果 code 是 4003 说明该 apikey 没有可用请求次数
                return None

            if resp_payload['results']:
                for result in resp_payload['results']:
                    if result['resultType'] == 'text':
                        # 返回文本类型的回复
                        return result['values']['text']
    except (httpx.HTTPError, json.JSONDecodeError, KeyError):
        # 抛出上面任何异常，说明调用失败
        return None
