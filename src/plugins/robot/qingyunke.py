""" 青云客智能聊天机器人
"""
import json
from typing import Optional

import aiohttp
from nonebot import CommandSession
from nonebot.helpers import context_id


async def call_qingyunke_api(session: CommandSession,
                             text: str) -> Optional[str]:
    """ 调用青云客智能聊天机器人 API
    """
    if not text:
        return None

    # 构造请求数据
    url = f'http://api.qingyunke.com/api.php?key=free&appid=0&msg={text}'

    try:
        # 使用 aiohttp 库发送最终的请求
        async with aiohttp.ClientSession() as sess:
            async with sess.post(url) as response:
                if response.status != 200:
                    # 如果 HTTP 响应状态码不是 200，说明调用失败
                    return None

                resp_payload = json.loads(await response.text())

                if resp_payload['result'] != 0:
                    # 如果 result 不是 0，说明出错
                    return None

                return resp_payload['content'].replace('{br}', '\n').replace(
                    '菲菲翻译', '小誓约翻译')
    except (aiohttp.ClientError, json.JSONDecodeError, KeyError):
        # 抛出上面任何异常，说明调用失败
        return None
