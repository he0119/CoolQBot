import asyncio
import base64
import os
import re
from html import escape
from time import asctime
from typing import Optional

from bs4 import BeautifulSoup as bs
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.log import logger
from playwright.async_api import async_playwright

from .plugin_config import plugin_config


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Render(metaclass=Singleton):
    def __init__(self):
        self.interval_log = ""
        self.remote_browser = False

    async def render(
        self,
        url: str,
        target: Optional[str] = None,
    ) -> Optional[bytes]:
        retry_times = 0
        while retry_times < 3:
            try:
                return await asyncio.wait_for(self.do_render(url, target), 20)
            except asyncio.TimeoutError:
                retry_times += 1
                logger.warning(
                    "render error {}\n".format(retry_times) + self.interval_log
                )
                self.interval_log = ""
                # if self.browser:
                #     await self.browser.close()
                #     self.lock.release()

    def _inter_log(self, message: str) -> None:
        self.interval_log += asctime() + "" + message + "\n"

    async def do_render(
        self,
        url: str,
        target: Optional[str] = None,
    ) -> Optional[bytes]:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            self._inter_log("open browser")
            page = await browser.new_page()
            await page.goto(url)
            self._inter_log("open page")
            if target:
                target_ele = await page.query_selector(target)
                if not target_ele:
                    return None
                data = await target_ele.screenshot(type="jpeg")
            else:
                data = await page.screenshot(type="jpeg")
            self._inter_log("screenshot")
            await browser.close()
            self._inter_log("close browser")
            assert isinstance(data, bytes)
            return data

    async def text_to_pic(self, text: str) -> Optional[bytes]:
        lines = text.split("\n")
        parsed_lines = list(map(lambda x: "<p>{}</p>".format(escape(x)), lines))
        html_text = '<div style="width:17em;padding:1em">{}</div>'.format(
            "".join(parsed_lines)
        )
        url = "data:text/html;charset=UTF-8;base64,{}".format(
            base64.b64encode(html_text.encode()).decode()
        )
        data = await self.render(url, target="div")
        return data

    async def text_to_pic_cqcode(self, text: str) -> MessageSegment:
        data = await self.text_to_pic(text)
        if data:
            return MessageSegment.image(data)
        else:
            return MessageSegment.text("生成图片错误")


async def parse_text(text: str) -> MessageSegment:
    "return raw text if don't use pic, otherwise return rendered opcode"
    if plugin_config.bison_use_pic:
        render = Render()
        return await render.text_to_pic_cqcode(text)
    else:
        return MessageSegment.text(text)


def html_to_text(html: str, query_dict: dict = {}) -> str:
    html = re.sub(r"<br\s*/?>", "<br>\n", html)
    html = html.replace("</p>", "</p>\n")
    soup = bs(html, "html.parser")
    if query_dict:
        node = soup.find(**query_dict)
    else:
        node = soup
    assert node is not None
    return node.text.strip()
