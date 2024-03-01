"""记录每日委托"""

from datetime import datetime

from nonebot_plugin_datastore import get_plugin_data
from nonebot_plugin_user import get_user_by_id

from .mogu import add_mogu_info

plugin_data = get_plugin_data()

type QUEST_DATA = dict[str, list[str]]


def get_filename() -> str:
    now = datetime.now()
    return now.strftime("%Y-%m-%d") + ".json"


def get_quests_data() -> QUEST_DATA:
    filename = get_filename()
    if not plugin_data.exists(filename):
        plugin_data.dump_json({}, filename)
        return {}
    return plugin_data.load_json(filename)


def save_quests_data(data: QUEST_DATA):
    filename = get_filename()
    plugin_data.dump_json(data, filename)


# async def get_daily_quests(user_id: int) -> str:
#     """获取每日委托"""
#     data = get_quests_data()
#     quests = data.get(str(user_id), [])
#     quests = [await add_mogu_info(quest) for quest in quests]
#     return (
#         f"你的每日委托为：{', '.join(quests)}" if quests else "你还没有设置每日委托。"
#     )


def set_daily_quests(user_id: int, quests: list[str]):
    """设置每日委托"""
    data = get_quests_data()
    data[str(user_id)] = quests
    save_quests_data(data)


async def get_usernames(users: list[int]) -> str:
    """获取用户名"""
    user_names = []
    for user_id in users:
        user = await get_user_by_id(user_id)
        user_names.append(user.name)

    return ", ".join(user_names)


async def get_daily_quests_pair(user_id: int) -> str:
    """获取与自己每日委托相同的群友"""
    data = get_quests_data()
    my_quests = data.get(str(user_id), [])
    if not my_quests:
        return "你还没有设置每日委托。"

    pair = {quest: [] for quest in my_quests}
    for user, quests in data.items():
        if user == str(user_id):
            continue
        for quest in quests:
            if quest in my_quests:
                pair[quest].append(user)

    msg = "与你每日委托相同的群友：\n"
    for quest, users in pair.items():
        quest = await add_mogu_info(quest)
        if users:
            msg += f"{quest}：{await get_usernames(users)}\n"
        else:
            msg += f"{quest}：无\n"

    return msg.strip()
