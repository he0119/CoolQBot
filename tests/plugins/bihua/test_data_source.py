"""测试壁画数据源"""

import hashlib

import pytest
from nonebug import App

from .utils import FAKE_IMAGE, FAKE_IMAGE_2


@pytest.fixture
async def bihua_service(app: App):
    """获取壁画服务实例"""
    from src.plugins.bihua.data_source import BihuaService

    return BihuaService()


async def test_add_bihua_success(bihua_service):
    """测试成功添加壁画"""
    await bihua_service.add_bihua(user_id=10, session_id="test_session", name="测试壁画", image_data=FAKE_IMAGE)

    # 检查壁画是否添加成功
    bihua = await bihua_service.get_bihua_by_name("测试壁画", "test_session")
    assert bihua is not None
    assert bihua.name == "测试壁画"
    assert bihua.user_id == 10
    assert bihua.session_id == "test_session"
    assert bihua.image_hash == hashlib.md5(FAKE_IMAGE).hexdigest()

    # 检查图片文件是否存在
    assert bihua.image_path().exists()


async def test_add_bihua_duplicate(bihua_service):
    """测试添加重复壁画"""
    # 先添加一个壁画
    await bihua_service.add_bihua(user_id=10, session_id="test_session", name="测试壁画", image_data=FAKE_IMAGE)

    # 尝试添加相同hash的壁画
    with pytest.raises(ValueError, match="相同的壁画已经存在"):
        await bihua_service.add_bihua(user_id=11, session_id="test_session", name="另一个名字", image_data=FAKE_IMAGE)


async def test_get_bihua_by_name_found(bihua_service):
    """测试根据名称获取壁画（找到）"""
    await bihua_service.add_bihua(user_id=10, session_id="test_session", name="测试壁画", image_data=FAKE_IMAGE)

    bihua = await bihua_service.get_bihua_by_name("测试壁画", "test_session")
    assert bihua is not None
    assert bihua.name == "测试壁画"


async def test_get_bihua_by_name_not_found(bihua_service):
    """测试根据名称获取壁画（未找到）"""
    bihua = await bihua_service.get_bihua_by_name("不存在的壁画", "test_session")
    assert bihua is None


async def test_search_bihua_found(bihua_service):
    """测试搜索壁画（找到结果）"""
    await bihua_service.add_bihua(user_id=10, session_id="test_session", name="测试壁画", image_data=FAKE_IMAGE)
    await bihua_service.add_bihua(user_id=11, session_id="test_session", name="另一个测试", image_data=FAKE_IMAGE_2)

    # 搜索包含"测试"的壁画
    result = await bihua_service.search_bihua("测试", "test_session")
    assert len(result) == 2

    # 搜索特定名称
    result = await bihua_service.search_bihua("壁画", "test_session")
    assert len(result) == 1
    assert result[0].name == "测试壁画"


async def test_search_bihua_not_found(bihua_service):
    """测试搜索壁画（未找到结果）"""
    result = await bihua_service.search_bihua("不存在", "test_session")
    assert len(result) == 0


async def test_get_all_bihua(bihua_service):
    """测试获取所有壁画"""
    await bihua_service.add_bihua(user_id=10, session_id="test_session", name="壁画1", image_data=FAKE_IMAGE)
    await bihua_service.add_bihua(user_id=11, session_id="test_session", name="壁画2", image_data=FAKE_IMAGE_2)

    # 获取该session的所有壁画
    result = await bihua_service.get_all_bihua("test_session")
    assert len(result) == 2

    # 另一个session应该没有壁画
    result = await bihua_service.get_all_bihua("other_session")
    assert len(result) == 0


async def test_delete_bihua_success(bihua_service):
    """测试成功删除壁画"""
    await bihua_service.add_bihua(user_id=10, session_id="test_session", name="测试壁画", image_data=FAKE_IMAGE)

    # 确认壁画存在
    bihua = await bihua_service.get_bihua_by_name("测试壁画", "test_session")
    assert bihua is not None
    image_path = bihua.image_path()
    assert image_path.exists()

    # 删除壁画
    await bihua_service.delete_bihua("测试壁画", "test_session")

    # 确认壁画已删除
    bihua = await bihua_service.get_bihua_by_name("测试壁画", "test_session")
    assert bihua is None

    # 确认图片文件已删除
    assert not image_path.exists()


async def test_delete_bihua_not_found(bihua_service):
    """测试删除不存在的壁画"""
    with pytest.raises(ValueError, match="壁画不存在"):
        await bihua_service.delete_bihua("不存在的壁画", "test_session")


async def test_get_user_bihua_count(bihua_service):
    """测试统计用户收藏的壁画数量"""
    # 用户10收藏2个壁画
    await bihua_service.add_bihua(user_id=10, session_id="test_session", name="壁画1", image_data=FAKE_IMAGE)
    await bihua_service.add_bihua(user_id=10, session_id="test_session", name="壁画2", image_data=FAKE_IMAGE_2)

    # 用户11收藏1个壁画
    fake_image_3 = b"fake_image_3_content"
    await bihua_service.add_bihua(user_id=11, session_id="test_session", name="壁画3", image_data=fake_image_3)

    # 统计结果
    result = await bihua_service.get_user_bihua_count("test_session")
    result_dict = dict(result)

    assert result_dict[10] == 2
    assert result_dict[11] == 1


async def test_session_isolation(bihua_service):
    """测试不同session之间的数据隔离"""
    # 在不同session中添加同名壁画
    await bihua_service.add_bihua(user_id=10, session_id="session_1", name="测试壁画", image_data=FAKE_IMAGE)
    await bihua_service.add_bihua(user_id=11, session_id="session_2", name="测试壁画", image_data=FAKE_IMAGE_2)

    # 检查session_1中的壁画
    bihua1 = await bihua_service.get_bihua_by_name("测试壁画", "session_1")
    assert bihua1 is not None
    assert bihua1.user_id == 10

    # 检查session_2中的壁画
    bihua2 = await bihua_service.get_bihua_by_name("测试壁画", "session_2")
    assert bihua2 is not None
    assert bihua2.user_id == 11

    # 确认它们是不同的壁画
    assert bihua1.id != bihua2.id
    assert bihua1.image_hash != bihua2.image_hash
