"""测试壁画工具函数"""

from pathlib import Path

from nonebug import App


async def test_get_image_path(app: App):
    """测试获取图片路径函数"""
    from src.plugins.bihua.utils import get_image_path

    # 测试路径生成
    path = get_image_path("test_group", "abc123")

    assert isinstance(path, Path)
    assert path.name == "abc123"
    assert path.parent.name == "test_group"


async def test_get_image_path_with_different_params(app: App):
    """测试不同参数的图片路径生成"""
    from src.plugins.bihua.utils import get_image_path

    # 测试不同的group_id和hash
    path1 = get_image_path("group_1", "hash_1")
    path2 = get_image_path("group_2", "hash_2")
    path3 = get_image_path("group_1", "hash_2")

    # 确保路径不同
    assert path1 != path2
    assert path1 != path3
    assert path2 != path3

    # 确保相同参数产生相同路径
    path1_duplicate = get_image_path("group_1", "hash_1")
    assert path1 == path1_duplicate
