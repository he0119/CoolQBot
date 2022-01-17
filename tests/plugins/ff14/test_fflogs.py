import pytest
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.ff14",)], indirect=True)
async def test_dps_missing_token(app: App):
    """测试 FFLOGS，缺少 Token 的情况"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.ff14 import fflogs_cmd

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/dps me"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            "对不起，Token 未设置，无法查询数据。\n请先使用命令\n/dps token <token>\n配置好 Token 后再尝试查询数据。",
            "result",
        )
        ctx.should_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.plugins.ff14",)], indirect=True)
async def test_dps_help(
    app: App,
    mocker: MockerFixture,
):
    """测试 FFLOGS，直接发送 /dps 命令的情况"""
    from nonebot.adapters.onebot.v11 import Message

    from src.plugins.ff14 import fflogs_cmd

    get_command_help = mocker.patch("src.plugins.ff14.get_command_help")
    get_command_help.return_value = Message("test")

    async with app.test_matcher(fflogs_cmd) as ctx:
        bot = ctx.create_bot()
        event = fake_group_message_event(message=Message("/dps"))

        ctx.receive_event(bot, event)
        ctx.should_call_send(event, Message("test"), "")
        ctx.should_finished()

    get_command_help.assert_called_once_with("ff14.dps")
