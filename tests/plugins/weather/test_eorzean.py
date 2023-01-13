import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


async def test_eorzean(app: App, mocker: MockerFixture):
    """测试艾欧泽亚天气"""
    from nonebot import require
    from nonebot.adapters.onebot.v11 import Message

    require("src.plugins.weather")
    from src.plugins.weather import weather_cmd

    mocked_time = mocker.patch("src.plugins.weather.eorzean_api.time")
    mocked_time.time.return_value = 1641619586

    async with app.test_matcher(weather_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/天气 利姆萨·罗敏萨"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "利姆萨·罗敏萨上层甲板\n当前天气：碧空\n还剩13分34秒切换到天气：阴云\n还剩36分54秒切换到天气：碧空\n还剩1时0分14秒切换到天气：碧空\n还剩1时23分34秒切换到天气：晴朗\n还剩1时46分54秒切换到天气：碧空\n还剩2时10分14秒切换到天气：碧空\n还剩2时33分34秒切换到天气：碧空\n还剩2时56分54秒切换到天气：晴朗\n还剩3时20分14秒切换到天气：晴朗",
            "result",
        )
        ctx.should_finished()

    mocked_time.time.assert_called_once()
