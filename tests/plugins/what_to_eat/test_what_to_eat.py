import pytest
from nonebot import get_adapter
from nonebot.adapters.onebot.v11 import Adapter, Bot, Message, MessageSegment
from nonebug import App
from pytest_mock import MockerFixture

from tests.fake import fake_group_message_event_v11


@pytest.mark.parametrize(
    "message",
    [
        "吃什么",
        "吃啥？",
        "中午吃啥",
        "今天 中午吃什么？",
    ],
)
async def test_what_to_eat(app: App, mocker: MockerFixture, message: str):
    from src.plugins.what_to_eat import what_to_eat_cmd
    from src.plugins.what_to_eat.data_source import Food

    food = Food("火锅", "File:Hot pot dinner.jpg")
    recommend_food = mocker.patch("src.plugins.what_to_eat.recommend_food", return_value=food)
    get_food_image = mocker.patch("src.plugins.what_to_eat.get_food_image", return_value=None)

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message(message))
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, "推荐你吃：火锅！", "result", at_sender=True)
        ctx.should_finished(what_to_eat_cmd)

    recommend_food.assert_called_once_with()
    get_food_image.assert_awaited_once_with(food.commons_file)


async def test_what_to_eat_with_image(app: App, mocker: MockerFixture):
    from src.plugins.what_to_eat import what_to_eat_cmd
    from src.plugins.what_to_eat.data_source import Food
    from src.plugins.what_to_eat.image_api import FoodImage

    food = Food("火锅", "File:Hot pot dinner.jpg")
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
            + MessageSegment.text("推荐你吃：火锅！\n")
            + MessageSegment.image(b"image")
            + MessageSegment.text(
                "\n图片：测试作者｜CC BY-SA 4.0\n"
                "来源：https://commons.wikimedia.org/wiki/File:Hot_pot.jpg\n"
                "许可：https://creativecommons.org/licenses/by-sa/4.0/"
            ),
            True,
        )
        ctx.should_finished(what_to_eat_cmd)

    get_food_image.assert_awaited_once_with(food.commons_file)


async def test_what_to_eat_does_not_match_trailing_text(app: App):
    from src.plugins.what_to_eat import what_to_eat_cmd

    async with app.test_matcher() as ctx:
        adapter = get_adapter(Adapter)
        bot = ctx.create_bot(base=Bot, adapter=adapter)

        event = fake_group_message_event_v11(message=Message("我今天吃什么呀"))
        ctx.receive_event(bot, event)
        ctx.should_not_pass_rule(what_to_eat_cmd)


def test_recommend_food(mocker: MockerFixture):
    from src.plugins.what_to_eat.data_source import FOODS, Food, recommend_food

    food = Food("火锅", "File:Hot pot dinner.jpg")
    choice = mocker.patch("src.plugins.what_to_eat.data_source.choice", return_value=food)

    assert recommend_food() == food
    choice.assert_called_once_with(FOODS)


def test_foods_have_unique_commons_files(app: App):
    from src.plugins.what_to_eat.data_source import FOODS

    assert len(FOODS) == 60
    assert len({food.name for food in FOODS}) == len(FOODS)
    assert len({food.commons_file for food in FOODS}) == len(FOODS)
    assert all(food.commons_file.startswith("File:") for food in FOODS)
