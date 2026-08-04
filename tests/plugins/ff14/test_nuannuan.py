import json
from pathlib import Path

import httpx
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11

DOC_URL = "https://docs.qq.com/sheet/DY2lCeEpwemZESm5q?tab=BB08J2&c=A1A0A0"
DETAIL_URL = "https://docs.qq.com/sheet/DY2lCeEpwemZESm5q?tab=dewveu&c=A1A0A0"
OPEN_DOC_URL = "https://docs.qq.com/dop-api/opendoc?fixture=primary"
OPEN_DETAIL_URL = "https://docs.qq.com/dop-api/opendoc?fixture=detail"


def _response(url: str, text: str) -> httpx.Response:
    return httpx.Response(200, text=text, request=httpx.Request("GET", url))


async def test_nuannuan(app: App, mocker: MockerFixture):
    """从腾讯文档主表定位当前期数，并用详情表补全攻略。"""
    from src.plugins.ff14.plugins.ff14_nuannuan import nuannuan_cmd

    with open(Path(__file__).parent / "nuannuan_opendoc.json", encoding="utf-8") as file:
        open_doc_payload = json.load(file)
    callback = f"clientVarsCallback({json.dumps(open_doc_payload, ensure_ascii=False)})"
    async_client = mocker.patch("httpx.AsyncClient.get")
    async_client.side_effect = [
        _response(DOC_URL, f'<script src="{OPEN_DOC_URL}"></script>'),
        _response(OPEN_DOC_URL, callback),
        _response(DETAIL_URL, f'<script src="{OPEN_DETAIL_URL}"></script>'),
        _response(OPEN_DETAIL_URL, callback),
    ]

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/时尚品鉴"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "游玩C哩酱 FF14 时尚品鉴第444期\n"
            "主题：风信子冒险者\n"
            "【头部防具】提示内容：风信子\n"
            "——往期：第 372 期\n"
            "X色风信子头花（炼金术师：73级）\n"
            "【身体防具】提示内容：西格玛\n"
            "——往期：第 440 期\n"
            "碳硅晶XX战甲/长衣/长袍（70级大型：O5-O8低保兑换）\n"
            "钻石XX战甲/长衣/长袍（70级大型（零式）：O8S）\n"
            "【手部防具】提示内容：冒险的开始\n"
            "——往期：第 359 期\n"
            "各种族初始装备\n"
            "【腿部防具】提示内容：装饰钉扣\n"
            "——往期：第 257 期\n"
            "青麻强袭/精准/游击软甲裤\n"
            "歹徒制敌/强袭/游击软甲裤\n"
            "完整攻略：https://www.youwanc.com/\n"
            f"腾讯文档：{DOC_URL}",
            True,
        )
        ctx.should_finished(nuannuan_cmd)

    assert async_client.await_args_list == [
        mocker.call(DOC_URL),
        mocker.call(OPEN_DOC_URL, headers={"Referer": DOC_URL}),
        mocker.call(DETAIL_URL),
        mocker.call(OPEN_DETAIL_URL, headers={"Referer": DETAIL_URL}),
    ]


async def test_nuannuan_falls_back_to_links(mocker: MockerFixture):
    """网页暂时不可访问时仍返回可手动打开的攻略入口。"""
    from src.plugins.ff14.plugins.ff14_nuannuan.data_source import get_latest_nuannuan

    mocker.patch("httpx.AsyncClient.get", side_effect=httpx.ConnectError("unavailable"))

    result = await get_latest_nuannuan()

    assert result == (f"游玩C哩酱 FF14 时尚品鉴本期攻略\n攻略站：https://www.youwanc.com/\n腾讯文档：{DOC_URL}")
