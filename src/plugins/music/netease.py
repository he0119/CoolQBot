""" 网易云音乐
"""
import json
from typing import Optional

import aiohttp


async def call_netease_api(name: str) -> Optional[str]:
    """ 网易云搜索 API
    """
    if not name:
        return None

    # 构造请求数据
    url = f'https://music.aityp.com/search?keywords={name}'

    try:
        # 使用 aiohttp 库发送最终的请求
        async with aiohttp.ClientSession() as sess:
            async with sess.post(url) as response:
                if response.status != 200:
                    # 如果 HTTP 响应状态码不是 200，说明调用失败
                    return None

                resp_payload = json.loads(await response.text())

                if resp_payload['code'] != 200:
                    # 如果 code 不是 200，说明出错
                    return None

                # 获取音乐 ID，并返回对应的 CQ 码
                music_id = resp_payload['result']['songs'][0]['id']
                return f'[CQ:music,type=163,id={music_id}]'

    except (aiohttp.ClientError, json.JSONDecodeError, KeyError):
        # 抛出上面任何异常，说明调用失败
        return None
