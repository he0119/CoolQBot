import pytest
from nonebug import App


async def test_bind_group_service(app: App):
    """测试群组绑定服务"""
    from src.utils.group_bind.data_source import group_bind_service

    # 测试绑定群组
    await group_bind_service.bind_group("group1", "group2")

    # 测试检查是否绑定
    is_bound = await group_bind_service.is_group_bound("group1")
    assert is_bound is True

    # 测试获取绑定ID
    bind_id = await group_bind_service.get_bind_id("group1")
    assert bind_id == "group2"

    # 测试更新绑定
    await group_bind_service.bind_group("group1", "group3")
    bind_id = await group_bind_service.get_bind_id("group1")
    assert bind_id == "group3"


async def test_unbind_group_service(app: App):
    """测试解绑群组服务"""
    from src.utils.group_bind.data_source import group_bind_service

    # 先绑定一个群组
    await group_bind_service.bind_group("group1", "group2")

    # 确认绑定存在
    is_bound = await group_bind_service.is_group_bound("group1")
    assert is_bound is True

    # 解绑群组
    await group_bind_service.unbind_group("group1")

    # 确认绑定已移除
    is_bound = await group_bind_service.is_group_bound("group1")
    assert is_bound is False


async def test_unbind_nonexistent_group(app: App):
    """测试解绑不存在的群组"""
    from src.utils.group_bind.data_source import group_bind_service

    # 尝试解绑不存在的群组，应该抛出异常
    with pytest.raises(ValueError, match="该群组未绑定到任何群组"):
        await group_bind_service.unbind_group("nonexistent_group")


async def test_get_bind_id_unbound_group(app: App):
    """测试获取未绑定群组的ID（应该返回自身）"""
    from src.utils.group_bind.data_source import group_bind_service

    # 获取未绑定群组的ID，应该返回自身的session_id
    bind_id = await group_bind_service.get_bind_id("unbound_group")
    assert bind_id == "unbound_group"


async def test_is_group_bound_false(app: App):
    """测试检查未绑定的群组"""
    from src.utils.group_bind.data_source import group_bind_service

    # 检查未绑定的群组
    is_bound = await group_bind_service.is_group_bound("unbound_group")
    assert is_bound is False


async def test_get_bound_session_ids(app: App):
    """测试获取所有绑定的会话ID列表"""
    from src.utils.group_bind.data_source import group_bind_service

    # 创建多个绑定到同一目标的群组
    await group_bind_service.bind_group("group1", "target_group")
    await group_bind_service.bind_group("group2", "target_group")
    await group_bind_service.bind_group("group3", "other_target")

    # 获取绑定到target_group的所有会话ID
    bound_session_ids = await group_bind_service.get_bound_session_ids("group1")
    assert set(bound_session_ids) == {"target_group", "group1", "group2"}

    # 从目标群组的角度获取绑定的会话ID
    bound_session_ids = await group_bind_service.get_bound_session_ids("target_group")
    assert set(bound_session_ids) == {"target_group", "group1", "group2"}

    # 获取绑定到other_target的会话ID
    bound_session_ids = await group_bind_service.get_bound_session_ids("group3")
    assert set(bound_session_ids) == {"other_target", "group3"}

    # 测试未绑定的群组
    bound_session_ids = await group_bind_service.get_bound_session_ids("unbound_group")
    assert bound_session_ids == ["unbound_group"]
