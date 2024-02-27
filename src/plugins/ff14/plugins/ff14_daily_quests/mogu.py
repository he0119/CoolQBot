""" 莫古莫古大收集

https://actff1.web.sdo.com/project/20231113mogu/index.html

生成
"""

import json
import re
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from nonebot_plugin_datastore import get_plugin_data

plugin_data = get_plugin_data()


MOGU_DATA = plugin_data.network_file(
    "https://raw.githubusercontent.com/he0119/CoolQBot/master/src/plugins/ff14/plugins/ff14_daily_quests/mogu.json",
    "mogu_data.json",
    cache=True,
)


async def add_mogu_info(name: str) -> str:
    """添加莫古莫古大收集的信息"""
    data = await MOGU_DATA.data
    if name in data:
        return f"{name}（{data[name]}）"
    return name


def update_json():
    """更新莫古莫古大收集的 json 文件"""
    html_doc = httpx.get(
        "https://actff1.web.sdo.com/project/20231113mogu/index.html"
    ).text

    soup = BeautifulSoup(html_doc, "html.parser")

    objectives = soup.find(id="objectives")

    contents = objectives.find_all("div", class_="objectives__content")  # type: ignore

    mogu_dict = {}

    for content in contents:
        title = content.find("h2").text
        # 提取标题中的数字
        numbers = re.findall(r"\d+", title)
        numbers_str = "/".join(numbers)
        # 副本
        dungeons = content.find(class_="objectives__inner")
        for dungeon in dungeons.find_all("h2"):
            mogu_dict[dungeon.text] = numbers_str

    MOGU_JSON_PATH = Path(__file__).parent / "mogu.json"
    with open(MOGU_JSON_PATH, "w", encoding="utf8") as f:
        json.dump(mogu_dict, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    update_json()
