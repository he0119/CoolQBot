import json
from datetime import date
from pathlib import Path

import httpx
import pytest
import respx
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


@pytest.fixture(autouse=True)
async def clear_food_data(app: App, mocker: MockerFixture):
    from src.plugins.what_to_eat.data_source import FOODS_DATA

    FOODS_DATA.clear_memory_cache()


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("/what_to_eat", "推荐你吃：火锅！"),
        ("/吃什么", "推荐你吃：火锅！"),
        ("吃什么", "推荐你吃：火锅！"),
        ("吃啥？", "推荐你吃：火锅！"),
        ("中午吃啥", "中午吃火锅！"),
        ("今晚吃什么？", "今晚吃火锅！"),
        ("今天 中午吃什么？", "今天中午吃火锅！"),
    ],
)
async def test_what_to_eat(app: App, mocker: MockerFixture, message: str, expected: str):
    from src.plugins.what_to_eat import what_to_eat_cmd
    from src.plugins.what_to_eat.data_source import Food, FoodImageRef

    food = Food("火锅", FoodImageRef("commons", "File:Chengdu hot pot.jpg"))
    recommend_food = mocker.patch("src.plugins.what_to_eat.recommend_food", return_value=food)
    get_food_image = mocker.patch("src.plugins.what_to_eat.get_food_image", return_value=None)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message(message))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, "result", at_sender=True)
        ctx.should_finished(what_to_eat_cmd)

    recommend_food.assert_awaited_once_with()
    get_food_image.assert_awaited_once_with(food.image)


async def test_what_to_eat_with_image(app: App, mocker: MockerFixture):
    from src.plugins.what_to_eat import what_to_eat_cmd
    from src.plugins.what_to_eat.data_source import Food, FoodImageRef
    from src.plugins.what_to_eat.image_api import FoodImage

    food = Food("火锅", FoodImageRef("commons", "File:Chengdu hot pot.jpg"))
    mocker.patch("src.plugins.what_to_eat.recommend_food", return_value=food)
    get_food_image = mocker.patch(
        "src.plugins.what_to_eat.get_food_image",
        return_value=FoodImage(
            content=b"image",
            mimetype="image/jpeg",
            creator="测试作者",
            license_name="CC BY-SA 4.0",
            source_url="https://commons.wikimedia.org/wiki/File:Hot_pot.jpg",
            license_url="https://creativecommons.org/licenses/by-sa/4.0/",
        ),
    )

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("今晚吃什么"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            MessageSegment.at(10)
            + MessageSegment.text("今晚吃火锅！\n")
            + MessageSegment.image(b"image")
            + MessageSegment.text(
                "\n图片：测试作者｜CC BY-SA 4.0\n"
                "来源：https://commons.wikimedia.org/wiki/File:Hot_pot.jpg\n"
                "许可：https://creativecommons.org/licenses/by-sa/4.0/"
            ),
            True,
        )
        ctx.should_finished(what_to_eat_cmd)

    get_food_image.assert_awaited_once_with(food.image)


async def test_what_to_eat_does_not_match_trailing_text(app: App):
    from src.plugins.what_to_eat import what_to_eat_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("我今天吃什么呀"))
        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule(what_to_eat_cmd)


async def test_update_foods_data_requires_command_start(app: App, mocker: MockerFixture):
    from src.plugins.what_to_eat import FOODS_DATA, what_to_eat_cmd

    update = mocker.patch.object(FOODS_DATA, "update")

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("吃什么 update"))
        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule(what_to_eat_cmd)

    update.assert_not_awaited()


async def test_recommend_food(mocker: MockerFixture):
    from src.plugins.what_to_eat.data_source import FOODS_DATA, Food, FoodDataset, FoodImageRef, recommend_food

    food = Food("火锅", FoodImageRef("commons", "File:Chengdu hot pot.jpg"))
    mocker.patch.object(FOODS_DATA, "_data", FoodDataset(date(2026, 8, 11), (food,)))
    choice = mocker.patch("src.plugins.what_to_eat.data_source.choice", return_value=food)

    assert await recommend_food() == food
    choice.assert_called_once_with((food,))


def test_public_foods_data(app: App):
    import nonebot_plugin_localstore as store

    from src.plugins.what_to_eat.data_source import FOODS_DATA, process_data

    data_file = Path(__file__).parents[3] / "public" / "foods.json"
    data = json.loads(data_file.read_text(encoding="utf-8"))
    dataset = process_data(data)
    raw_foods = [food for category in data["categories"] for food in category["foods"]]

    assert dataset.version == date(2026, 8, 11)
    assert len(data["categories"]) == 12
    expected_images = {
        "火锅": ("commons", "File:Chengdu hot pot.jpg"),
        "串串香": ("openverse", "8e4f0401-a9ec-4a53-b521-eae1323d6ff7"),
        "刀削面": ("openverse", "70eba2cd-ffaa-4070-858d-db17e169e9a9"),
        "烤肉": ("openverse", "09cfa4d3-87db-405a-858c-7504b31cf359"),
        "番茄炒蛋": ("openverse", "274f3029-f595-40d0-ad68-2edff610f4af"),
        "轻食沙拉": ("openverse", "c8314f30-7bff-406f-b658-8d593ff80e0d"),
        "三明治": ("openverse", "7ef1012f-52dd-4162-8c21-979a6455a604"),
    }

    assert len(dataset.foods) == 89
    assert all("image" in food and "commons_file" not in food for food in raw_foods)
    assert sum(food.image.provider == "commons" for food in dataset.foods) == 83
    assert sum(food.image.provider == "openverse" for food in dataset.foods) == 6
    assert len({food.name for food in dataset.foods}) == len(dataset.foods)
    assert len({food.image.cache_key for food in dataset.foods}) == len(dataset.foods)
    assert "自选菜" not in {food.name for food in dataset.foods}
    assert {
        food.name: (food.image.provider, food.image.id) for food in dataset.foods if food.name in expected_images
    } == expected_images
    assert FOODS_DATA.cache_file == store.BASE_CACHE_DIR / "what_to_eat" / "foods.json"


def test_foods_data_rejects_invalid_openverse_id(app: App):
    from src.plugins.what_to_eat.data_source import process_data

    data = {
        "version": "2026-08-11",
        "categories": [
            {
                "name": "测试",
                "foods": [{"name": "测试菜", "image": {"provider": "openverse", "id": "not-a-uuid"}}],
            }
        ],
    }

    with pytest.raises(ValueError, match="Openverse 图片 ID"):
        process_data(data)


def test_foods_data_rejects_legacy_commons_file(app: App):
    from src.plugins.what_to_eat.data_source import process_data

    data = {
        "version": "2026-08-11",
        "categories": [
            {
                "name": "测试",
                "foods": [{"name": "测试菜", "commons_file": "File:Test.jpg"}],
            }
        ],
    }

    with pytest.raises(ValueError, match="图片格式错误"):
        process_data(data)


@pytest.mark.parametrize("version", [1, "1", "2026/08/11", "2026-8-11"])
def test_foods_data_rejects_invalid_version(app: App, version: object):
    from src.plugins.what_to_eat.data_source import process_data

    data_file = Path(__file__).parents[3] / "public" / "foods.json"
    data = json.loads(data_file.read_text(encoding="utf-8"))
    data["version"] = version

    with pytest.raises(ValueError, match="美食数据版本"):
        process_data(data)


@respx.mock
async def test_recommend_food_downloads_public_data(app: App, mocker: MockerFixture):
    from src.plugins.what_to_eat.data_source import FOODS_DATA, FOODS_DATA_URL, recommend_food

    data_file = Path(__file__).parents[3] / "public" / "foods.json"
    data = json.loads(data_file.read_text(encoding="utf-8"))
    request = respx.get(FOODS_DATA_URL).mock(return_value=httpx.Response(200, json=data))
    choice = mocker.patch("src.plugins.what_to_eat.data_source.choice", side_effect=lambda foods: foods[0])

    food = await recommend_food()

    assert food.name == "火锅"
    assert request.call_count == 1
    assert FOODS_DATA.cache_file.is_file()
    choice.assert_called_once()


@pytest.mark.parametrize(
    ("user_id", "command", "message", "updated"),
    [
        (10, "/what_to_eat update", "美食数据更新成功，数据日期：2026-08-11", True),
        (10000, "/吃什么 update", "该指令仅管理员可用", False),
    ],
)
async def test_update_foods_data(
    app: App,
    mocker: MockerFixture,
    user_id: int,
    command: str,
    message: str,
    updated: bool,
):
    from src.plugins.what_to_eat import FOODS_DATA, what_to_eat_cmd
    from src.plugins.what_to_eat.data_source import FoodDataset

    update = mocker.patch.object(FOODS_DATA, "update", return_value=FoodDataset(date(2026, 8, 11), ()))

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message(command), user_id=user_id)
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, message, "result", at_sender=True)
        ctx.should_finished(what_to_eat_cmd)

    if updated:
        update.assert_awaited_once_with()
    else:
        update.assert_not_awaited()


async def test_update_foods_data_failure(app: App, mocker: MockerFixture):
    from src.plugins.what_to_eat import FOODS_DATA, what_to_eat_cmd
    from src.utils.remote_data import RemoteDataError

    mocker.patch.object(FOODS_DATA, "update", side_effect=RemoteDataError("unavailable"))

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("/what_to_eat update"))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "美食数据更新失败，已保留原缓存", "result", at_sender=True)
        ctx.should_finished(what_to_eat_cmd)
