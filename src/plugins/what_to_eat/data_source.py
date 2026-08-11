"""随机美食推荐数据。"""

from dataclasses import dataclass
from datetime import date
from random import choice

from nonebot_plugin_localstore import get_plugin_cache_dir

from src.utils.remote_data import RemoteJsonData

FOODS_DATA_URL = "https://bot-docs.hehome.xyz/foods.json"


@dataclass(frozen=True)
class Food:
    """美食名称及人工挑选的 Wikimedia Commons 文件。"""

    name: str
    commons_file: str


@dataclass(frozen=True)
class FoodDataset:
    """已校验的美食数据及其发布日期。"""

    version: date
    foods: tuple[Food, ...]


def process_data(data: object) -> FoodDataset:
    """校验并展开按菜系分类的美食数据。"""
    if not isinstance(data, dict):
        raise ValueError("不支持的美食数据格式")

    version = data.get("version")
    if not isinstance(version, str):
        raise ValueError("美食数据版本必须是日期")
    try:
        version_date = date.fromisoformat(version)
    except ValueError as e:
        raise ValueError("美食数据版本必须是 YYYY-MM-DD 格式的日期") from e
    if version_date.isoformat() != version:
        raise ValueError("美食数据版本必须是 YYYY-MM-DD 格式的日期")

    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        raise ValueError("美食数据中没有分类")

    foods: list[Food] = []
    for category in categories:
        if not isinstance(category, dict) or not isinstance(category.get("name"), str):
            raise ValueError("美食分类格式错误")
        category_foods = category.get("foods")
        if not isinstance(category_foods, list) or not category_foods:
            raise ValueError(f"美食分类 {category['name']} 为空")
        for item in category_foods:
            if not isinstance(item, dict):
                raise ValueError("美食条目格式错误")
            name = item.get("name")
            commons_file = item.get("commons_file")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("美食名称不能为空")
            if not isinstance(commons_file, str) or not commons_file.startswith("File:"):
                raise ValueError(f"美食 {name} 的 Wikimedia Commons 文件名无效")
            foods.append(Food(name=name, commons_file=commons_file))

    if len({food.name for food in foods}) != len(foods):
        raise ValueError("美食名称不能重复")
    if len({food.commons_file for food in foods}) != len(foods):
        raise ValueError("Wikimedia Commons 文件名不能重复")
    return FoodDataset(version=version_date, foods=tuple(foods))


FOODS_DATA = RemoteJsonData(
    FOODS_DATA_URL,
    lambda: get_plugin_cache_dir() / "foods.json",
    process_data,
)


async def recommend_food() -> Food:
    """从已缓存的远程数据中随机选择一种美食。"""
    dataset = await FOODS_DATA.data
    return choice(dataset.foods)
