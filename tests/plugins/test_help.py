import nonebot
import nonebug
import pytest
from nonebug import Constructor


@pytest.mark.asyncio
async def test_help_plugin(bug):
    con = Constructor("Test help", "CQHTTP", "1")
    con.set_message("/help help", user_id=2, group_id=1)
    con.add_api(
        "send_msg",
        {
            "user_id": 2,
            "group_id": 1,
            "message": "获取帮助\n\n获取所有支持的命令\n/help all\n获取某个命令的帮助\n/help 命令名",
            "message_type": "group",
        },
        {"message_id": 123},
    )
    await con.test_plugin("src.plugins.help")
