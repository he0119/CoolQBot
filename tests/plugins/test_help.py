from pathlib import Path

import pytest
from nonebot.adapters.cqhttp.message import Message
from nonebug import Constructor


@pytest.mark.asyncio
async def test_help(nonebug_path: Path):
    name = "Test help"
    con = Constructor(name, "CQHTTP", "1")
    con.set_message("/help", user_id=2, group_id=1)
    con.add_api(
        "send_msg",
        {
            "user_id": 2,
            "group_id": 1,
            "message": Message("获取帮助\n\n获取所有支持的命令\n/help all\n获取某个命令的帮助\n/help 命令名"),
            "message_type": "group",
        },
        {"message_id": 1},
    )
    await con.test_plugin("src.plugins.help", log_name=name)

    out_file = nonebug_path / f"{name}.log"
    err_file = nonebug_path / f"{name}_err.log"
    assert out_file.exists()
    assert err_file.exists() is False


@pytest.mark.asyncio
async def test_help_help(nonebug_path: Path):
    name = "Test help help"
    con = Constructor(name, "CQHTTP", "1")
    con.set_message("/help help", user_id=2, group_id=1)
    con.add_api(
        "send_msg",
        {
            "user_id": 2,
            "group_id": 1,
            "message": Message("获取帮助\n\n获取所有支持的命令\n/help all\n获取某个命令的帮助\n/help 命令名"),
            "message_type": "group",
        },
        {"message_id": 1},
    )
    await con.test_plugin("src.plugins.help", log_name=name)

    out_file = nonebug_path / f"{name}.log"
    err_file = nonebug_path / f"{name}_err.log"
    assert out_file.exists()
    assert err_file.exists() is False


@pytest.mark.asyncio
async def test_help_all(nonebug_path: Path):
    name = "Test help all"
    con = Constructor(name, "CQHTTP", "1")
    con.set_message("/help all", user_id=2, group_id=1)
    con.add_api(
        "send_msg",
        {
            "user_id": 2,
            "group_id": 1,
            "message": Message("命令（别名）列表：\nhelp(帮助)"),
            "message_type": "group",
        },
        {"message_id": 1},
    )
    await con.test_plugin("src.plugins.help", log_name=name)

    out_file = nonebug_path / f"{name}.log"
    err_file = nonebug_path / f"{name}_err.log"
    assert out_file.exists()
    assert err_file.exists() is False
