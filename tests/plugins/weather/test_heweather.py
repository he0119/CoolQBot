import json
from pathlib import Path

import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


def mocked_get(url: str):
    class MockResponse:
        def __init__(self, json: dict):
            self._json = json

        def json(self):
            return self._json

    test_dir = Path(__file__).parent
    if (
        url
        == "https://geoapi.qweather.com/v2/city/lookup?location=%E6%88%90%E9%83%BD&key=1234567890"
        or url
        == "https://geoapi.qweather.com/v2/city/lookup?location=%E6%88%90%E9%83%BD&adm=%E5%9B%9B%E5%B7%9D&key=1234567890"
    ):
        with open(test_dir / "lookup.json", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)
    if (
        url
        == "https://devapi.qweather.com/v7/weather/now?location=101270101&key=1234567890"
    ):
        with open(test_dir / "now.json", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)
    if (
        url
        == "https://devapi.qweather.com/v7/weather/3d?location=101270101&key=1234567890"
    ):
        with open(test_dir / "3d.json", encoding="utf-8") as f:
            data = json.load(f)
        return MockResponse(data)

    return MockResponse({})


async def test_heweather(app: App, mocker: MockerFixture):
    """测试和风天气"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.weather")
    from src.plugins.weather import weather_cmd
    from src.plugins.weather.heweather_api import plugin_config

    plugin_config.heweather_key = "1234567890"

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher(weather_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/天气 成都"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "中国 四川省 成都\n当前温度：9℃ 湿度：86%(体感温度：9℃)\n2022-01-08 阴转多云 温度：9~6℃ 峨眉月\n2022-01-09 多云转小雨 温度：10~7℃ 峨眉月\n2022-01-10 多云 温度：13~3℃ 上弦月",
            True,
        )
        ctx.should_finished()

    get.assert_has_calls(
        [
            mocker.call(
                "https://geoapi.qweather.com/v2/city/lookup?location=%E6%88%90%E9%83%BD&key=1234567890"
            ),  # type: ignore
            mocker.call(
                "https://devapi.qweather.com/v7/weather/now?location=101270101&key=1234567890"
            ),
            mocker.call(
                "https://devapi.qweather.com/v7/weather/3d?location=101270101&key=1234567890"
            ),
        ]
    )


async def test_heweather_with_adm(app: App, mocker: MockerFixture):
    """测试和风天气，带行政区划"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.weather")
    from src.plugins.weather import weather_cmd
    from src.plugins.weather.heweather_api import plugin_config

    plugin_config.heweather_key = "1234567890"

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher(weather_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/天气 成都 四川"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "中国 四川省 成都\n当前温度：9℃ 湿度：86%(体感温度：9℃)\n2022-01-08 阴转多云 温度：9~6℃ 峨眉月\n2022-01-09 多云转小雨 温度：10~7℃ 峨眉月\n2022-01-10 多云 温度：13~3℃ 上弦月",
            True,
        )
        ctx.should_finished()

    get.assert_has_calls(
        [
            mocker.call(
                "https://geoapi.qweather.com/v2/city/lookup?location=%E6%88%90%E9%83%BD&adm=%E5%9B%9B%E5%B7%9D&key=1234567890"
            ),  # type: ignore
            mocker.call(
                "https://devapi.qweather.com/v7/weather/now?location=101270101&key=1234567890"
            ),
            mocker.call(
                "https://devapi.qweather.com/v7/weather/3d?location=101270101&key=1234567890"
            ),
        ]
    )


async def test_heweather_with_three_args(app: App, mocker: MockerFixture):
    """测试和风天气，输入三个参数"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.weather")
    from src.plugins.weather import weather_cmd
    from src.plugins.weather.heweather_api import plugin_config

    plugin_config.heweather_key = "1234567890"

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher(weather_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/天气 成都 四川 啊哈哈"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "中国 四川省 成都\n当前温度：9℃ 湿度：86%(体感温度：9℃)\n2022-01-08 阴转多云 温度：9~6℃ 峨眉月\n2022-01-09 多云转小雨 温度：10~7℃ 峨眉月\n2022-01-10 多云 温度：13~3℃ 上弦月",
            True,
        )
        ctx.should_finished()

    get.assert_has_calls(
        [
            mocker.call(
                "https://geoapi.qweather.com/v2/city/lookup?location=%E6%88%90%E9%83%BD&adm=%E5%9B%9B%E5%B7%9D&key=1234567890"
            ),  # type: ignore
            mocker.call(
                "https://devapi.qweather.com/v7/weather/now?location=101270101&key=1234567890"
            ),
            mocker.call(
                "https://devapi.qweather.com/v7/weather/3d?location=101270101&key=1234567890"
            ),
        ]
    )
