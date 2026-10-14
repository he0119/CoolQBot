import pytest
from nonebug import App
from sqlalchemy import delete


@pytest.fixture
async def app(app: App):
    # Recorder 是进程级单例，`_enabled` 会缓存首次查询结果；
    # 其它插件的用例若在同一个群发过未被处理的消息，就会留下“未开启复读”的缓存
    from src.plugins.repeat.recorder import _RECORDER_REGISTRY

    _RECORDER_REGISTRY.clear()

    yield app

    # 清理数据库
    from nonebot_plugin_orm import get_session

    from src.plugins.repeat.models import Enabled, MessageRecord

    # 清除缓存
    _RECORDER_REGISTRY.clear()

    async with get_session() as session, session.begin():
        await session.execute(delete(MessageRecord))
        await session.execute(delete(Enabled))
