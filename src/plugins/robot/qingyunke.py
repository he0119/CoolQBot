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

    # 替换关键词，因为菲菲是这个机器人 API 的自称
    need_replace = False
    if '小誓约' in text:
        text = text.replace('小誓约', '菲菲')
        need_replace = True

    # 如果提到了菲菲则回复不认识
    if '菲菲' in text:
        return '不认识菲菲呢'

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

                r = resp_payload['content']
                # 替换一些奇怪的符号
                r = r.replace('{br}', '\n')
                r = r.replace('&lt;p&gt;　　', '')
                r = r.replace('&lt;/p&gt;', '')
                # 如果触发了关键词则需要替换回去
                if need_replace:
                    r = r.replace('菲菲', '小誓约').replace('梁浩小妾', '是大家最喜欢的人')

                return r
    except (aiohttp.ClientError, json.JSONDecodeError, KeyError):
        # 抛出上面任何异常，说明调用失败
        return None
