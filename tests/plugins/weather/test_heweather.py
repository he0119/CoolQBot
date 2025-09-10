import json
from pathlib import Path

from _pytest.logging import LogCaptureFixture
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


def mocked_get(url: str):
    class MockResponse:
        def __init__(self, json: dict):
            self._json = json

        def json(self):
            return self._json

    test_dir = Path(__file__).parent
    match url:
        case (
            "https://test.re.qweatherapi.com/geo/v2/city/lookup?location=%E6%88%90%E9%83%BD&key=1234567890"
            | "https://test.re.qweatherapi.com/geo/v2/city/lookup?location=%E6%88%90%E9%83%BD&adm=%E5%9B%9B%E5%B7%9D&key=1234567890"
        ):
            with open(test_dir / "lookup.json", encoding="utf-8") as f:
                data = json.load(f)
            return MockResponse(data)
        case "https://test.re.qweatherapi.com/v7/weather/now?location=101270101&key=1234567890":
            with open(test_dir / "now.json", encoding="utf-8") as f:
                data = json.load(f)
            return MockResponse(data)
        case "https://test.re.qweatherapi.com/v7/weather/3d?location=101270101&key=1234567890":
            with open(test_dir / "3d.json", encoding="utf-8") as f:
                data = json.load(f)
            return MockResponse(data)
        case "https://test.re.qweatherapi.com/geo/v2/city/lookup?location=fail&key=1234567890":
            return MockResponse({"code": "404"})

    return MockResponse({})


async def test_heweather(app: App, mocker: MockerFixture):
    """测试和风天气"""
    from src.plugins.weather import weather_cmd
    from src.plugins.weather.heweather_api import plugin_config

    mocker.patch.object(plugin_config, "heweather_host", "test.re.qweatherapi.com")
    mocker.patch.object(plugin_config, "heweather_key", "1234567890")

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/天气 成都"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "中国 四川省 成都\n当前温度：9℃ 湿度：86%(体感温度：9℃)\n2022-01-08 阴转多云 温度：9~6℃ 峨眉月\n2022-01-09 多云转小雨 温度：10~7℃ 峨眉月\n2022-01-10 多云 温度：13~3℃ 上弦月",
            True,
        )
        ctx.should_finished(weather_cmd)

    get.assert_has_calls(
        [
            mocker.call(
                "https://test.re.qweatherapi.com/geo/v2/city/lookup?location=%E6%88%90%E9%83%BD&key=1234567890"
            ),  # type: ignore
            mocker.call("https://test.re.qweatherapi.com/v7/weather/now?location=101270101&key=1234567890"),
            mocker.call("https://test.re.qweatherapi.com/v7/weather/3d?location=101270101&key=1234567890"),
        ]
    )


async def test_heweather_with_adm(app: App, mocker: MockerFixture):
    """测试和风天气，带行政区划"""
    from src.plugins.weather import weather_cmd
    from src.plugins.weather.heweather_api import plugin_config

    mocker.patch.object(plugin_config, "heweather_host", "test.re.qweatherapi.com")
    mocker.patch.object(plugin_config, "heweather_key", "1234567890")

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/天气 成都 四川"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "中国 四川省 成都\n当前温度：9℃ 湿度：86%(体感温度：9℃)\n2022-01-08 阴转多云 温度：9~6℃ 峨眉月\n2022-01-09 多云转小雨 温度：10~7℃ 峨眉月\n2022-01-10 多云 温度：13~3℃ 上弦月",
            True,
        )
        ctx.should_finished(weather_cmd)

    get.assert_has_calls(
        [
            mocker.call(
                "https://test.re.qweatherapi.com/geo/v2/city/lookup?location=%E6%88%90%E9%83%BD&adm=%E5%9B%9B%E5%B7%9D&key=1234567890"
            ),  # type: ignore
            mocker.call("https://test.re.qweatherapi.com/v7/weather/now?location=101270101&key=1234567890"),
            mocker.call("https://test.re.qweatherapi.com/v7/weather/3d?location=101270101&key=1234567890"),
        ]
    )


async def test_heweather_with_three_args(app: App, mocker: MockerFixture):
    """测试和风天气，输入三个参数"""
    from src.plugins.weather import weather_cmd
    from src.plugins.weather.heweather_api import plugin_config

    mocker.patch.object(plugin_config, "heweather_host", "test.re.qweatherapi.com")
    mocker.patch.object(plugin_config, "heweather_key", "1234567890")

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/天气 成都 四川 啊哈哈"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "中国 四川省 成都\n当前温度：9℃ 湿度：86%(体感温度：9℃)\n2022-01-08 阴转多云 温度：9~6℃ 峨眉月\n2022-01-09 多云转小雨 温度：10~7℃ 峨眉月\n2022-01-10 多云 温度：13~3℃ 上弦月",
            True,
        )
        ctx.should_finished(weather_cmd)

    get.assert_has_calls(
        [
            mocker.call(
                "https://test.re.qweatherapi.com/geo/v2/city/lookup?location=%E6%88%90%E9%83%BD&adm=%E5%9B%9B%E5%B7%9D&key=1234567890"
            ),  # type: ignore
            mocker.call("https://test.re.qweatherapi.com/v7/weather/now?location=101270101&key=1234567890"),
            mocker.call("https://test.re.qweatherapi.com/v7/weather/3d?location=101270101&key=1234567890"),
        ]
    )


async def test_heweather_lookup_failed(app: App, mocker: MockerFixture, caplog: LogCaptureFixture):
    """测试和风天气，城市查找失败"""
    from src.plugins.weather import weather_cmd
    from src.plugins.weather.heweather_api import plugin_config

    mocker.patch.object(plugin_config, "heweather_host", "test.re.qweatherapi.com")
    mocker.patch.object(plugin_config, "heweather_key", "1234567890")

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/天气 fail"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "我才不是因为不知道才不告诉你fail的天气呢",
            True,
        )
        ctx.should_finished(weather_cmd)

    get.assert_has_calls(
        [
            mocker.call("https://test.re.qweatherapi.com/geo/v2/city/lookup?location=fail&key=1234567890"),  # type: ignore
        ]
    )

    # 如果没有查询到城市，不应该有和风天气 API 请求失败的日志
    assert "和风天气 API 请求失败" not in caplog.text


async def test_heweather_got_path(app: App, mocker: MockerFixture):
    """测试和风天气，测试 got_path 交互功能"""
    from src.plugins.weather import weather_cmd
    from src.plugins.weather.heweather_api import plugin_config

    mocker.patch.object(plugin_config, "heweather_host", "test.re.qweatherapi.com")
    mocker.patch.object(plugin_config, "heweather_key", "1234567890")

    get = mocker.patch("httpx.AsyncClient.get", side_effect=mocked_get)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        # 首先发送不带参数的命令，应该触发 got_path 提示
        event = fake_group_message_event_v11(message=Message("/天气"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "你想查询哪个城市的天气呢？",
            "result",
        )
        ctx.should_rejected(weather_cmd)

        # 然后用户输入城市名，应该返回天气信息
        event = fake_group_message_event_v11(message=Message("成都"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "中国 四川省 成都\n当前温度：9℃ 湿度：86%(体感温度：9℃)\n2022-01-08 阴转多云 温度：9~6℃ 峨眉月\n2022-01-09 多云转小雨 温度：10~7℃ 峨眉月\n2022-01-10 多云 温度：13~3℃ 上弦月",
            True,
        )
        ctx.should_finished(weather_cmd)

    get.assert_has_calls(
        [
            mocker.call(
                "https://test.re.qweatherapi.com/geo/v2/city/lookup?location=%E6%88%90%E9%83%BD&key=1234567890"
            ),
            mocker.call("https://test.re.qweatherapi.com/v7/weather/now?location=101270101&key=1234567890"),
            mocker.call("https://test.re.qweatherapi.com/v7/weather/3d?location=101270101&key=1234567890"),
        ]  # type: ignore
    )
