""" 赛博查房 """
from nonebot import CommandGroup
from nonebot.adapters import Event, Message
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText, CommandArg
from nonebot.permission import USER
from nonebot.typing import T_State

from .data_source import Hospital

hospital_service = Hospital()

hospital = CommandGroup("hospital")

room_cmd = hospital.command("room", aliases={"查房", "赛博查房"})


@room_cmd.permission_updater
async def _(state: T_State, matcher: Matcher):
    if "user_id" in state:
        return USER(state["user_id"])
    return matcher.permission


@room_cmd.handle()
async def _(state: T_State, args: Message = CommandArg()):
    user_id = args.extract_plain_text()
    if user_id:
        await room_cmd.send(f"正在查房 {user_id}...")
        state["user_id"] = user_id
    else:
        patients = await hospital_service.get_patients()
        if not patients:
            await room_cmd.finish("当前没有住院病人")
        await room_cmd.finish(
            "\n".join(
                f"{patient.user_id} 入院时间： {patient.admitted_at}" for patient in patients
            )
        )


@room_cmd.got("content", prompt="请问你现在有什么不适吗？")
async def _(user_id: str = Arg(), content: str = ArgPlainText()):
    await hospital_service.add_record(user_id, content)
    await room_cmd.finish("记录成功")


admit_cmd = hospital.command("admit", aliases={"入院", "赛博入院"})


@admit_cmd.handle()
async def _(args: Message = CommandArg()):
    user_id = args.extract_plain_text()

    try:
        await hospital_service.admit_patient(user_id)
        await admit_cmd.finish(f"{user_id} 入院成功")
    except ValueError:
        await admit_cmd.finish(f"病人 {user_id} 已入院")


discharge_cmd = hospital.command("discharge", aliases={"出院", "赛博出院"})


@discharge_cmd.handle()
async def _(args: Message = CommandArg()):
    user_id = args.extract_plain_text()

    try:
        await hospital_service.discharge_patient(user_id)
        await discharge_cmd.finish(f"{user_id} 出院成功")
    except ValueError:
        await discharge_cmd.finish(f"病人 {user_id} 未入院")
