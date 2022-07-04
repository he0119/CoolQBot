import json
from pathlib import Path

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
async def test_nuannuan(app: App, mocker: MockerFixture):
    """测试时尚品鉴"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.ff14")

    from src.plugins.ff14.plugins.nuannuan import nuannuan_cmd

    with open(Path(__file__).parent / "nuannuan.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    async_client = mocker.patch("httpx.AsyncClient.get")
    r = mocker.MagicMock()
    r.json = mocker.MagicMock(return_value=data)
    async_client.return_value = r

    async with app.test_matcher(nuannuan_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/时尚品鉴"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "【FF14/时尚品鉴】第204期 满分攻略 12月24日 最终幻想14\n游玩C哩酱攻略站：www.youwanc.com\n-\n【12月24日 第204周时尚品鉴预告预测】\n主题：高贵的魔法师\n\n【身体防具】*提示内容：决斗者\n——*往期：116 92 57\n狂妄长衣 莽撞长衣 匿盗外套 鬼盗外套 红盗外套 瘟疫使者长衣 瘟疫医生长衣 \n60级副本地脉灵灯天狼星灯塔/草木庭园圣茉夏娜植物园\n\n【腿部防具】*提示内容：暗魔\n——*往期：169 139\n暗魔xx打底裤\n24人副本影之国获得\n\n【脚部防具】*提示内容：祭祀仪式\n——*往期：132 115\n真狮鹫革XX凉鞋/XX战靴\n70\nhttps://www.bilibili.com/video/BV1Pq4y1m7wK",
            "result",
        )
        ctx.should_finished()
