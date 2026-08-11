"""随机美食推荐数据。"""

from dataclasses import dataclass
from datetime import date
from random import choice
from typing import Literal
from uuid import UUID

from nonebot_plugin_localstore import get_plugin_cache_dir

from src.utils.remote_data import RemoteJsonData

FOODS_DATA_URL = "https://bot-docs.hehome.xyz/foods.json"

type FoodImageProvider = Literal["commons", "openverse"]


@dataclass(frozen=True)
class FoodImageRef:
    """人工挑选的图片来源及其稳定标识。"""

    provider: FoodImageProvider
    id: str

    @property
    def cache_key(self) -> str:
        """生成跨图片来源唯一的缓存键。"""
        return f"{self.provider}:{self.id}"


@dataclass(frozen=True)
class Food:
    """美食名称及人工挑选的图片。"""

    name: str
    image: FoodImageRef


@dataclass(frozen=True)
class FoodDataset:
    """已校验的美食数据及其发布日期。"""

    version: date
    foods: tuple[Food, ...]


def _parse_image_ref(item: dict[str, object], food_name: str) -> FoodImageRef:
    image = item.get("image")
    if not isinstance(image, dict):
        raise ValueError(f"美食 {food_name} 的图片格式错误")

    provider = image.get("provider")
    image_id = image.get("id")
    if not isinstance(image_id, str) or not image_id:
        raise ValueError(f"美食 {food_name} 的图片来源或标识无效")
    if provider == "commons":
        if not image_id.startswith("File:"):
            raise ValueError(f"美食 {food_name} 的 Wikimedia Commons 文件名无效")
        return FoodImageRef(provider="commons", id=image_id)
    if provider == "openverse":
        try:
            parsed_id = UUID(image_id)
        except ValueError as e:
            raise ValueError(f"美食 {food_name} 的 Openverse 图片 ID 无效") from e
        if str(parsed_id) != image_id:
            raise ValueError(f"美食 {food_name} 的 Openverse 图片 ID 无效")
        return FoodImageRef(provider="openverse", id=image_id)
    raise ValueError(f"美食 {food_name} 的图片来源或标识无效")


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
            if not isinstance(name, str) or not name.strip():
                raise ValueError("美食名称不能为空")
            foods.append(Food(name=name, image=_parse_image_ref(item, name)))

    if len({food.name for food in foods}) != len(foods):
        raise ValueError("美食名称不能重复")
    if len({food.image.cache_key for food in foods}) != len(foods):
        raise ValueError("美食图片不能重复")
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
