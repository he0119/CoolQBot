""" 赛博查房 """
from nonebot import CommandGroup, on_command
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.typing import T_State

from .data_source import Hospital

hospital_service = Hospital()

hospital = CommandGroup("hospital")

room = hospital.command("room", aliases={"查房", "赛博查房"})


@room.handle()
async def _(args: Message = CommandArg()):
    arg = args.extract_plain_text()

    patients = await hospital_service.get_patients()
    if not patients:
        await room.finish("当前没有住院病人")
    await room.finish(
        "\n".join(
            f"{patient.user_id} 入院时间： {patient.admitted_at}" for patient in patients
        )
    )


admit = hospital.command("admit", aliases={"入院", "赛博入院"})


@admit.handle()
async def _(args: Message = CommandArg()):
    user_id = args.extract_plain_text()

    try:
        await hospital_service.admit_patient(user_id)
        await admit.finish("入院成功")
    except ValueError:
        await admit.finish(f"病人 {user_id} 已入院")


discharge = hospital.command("discharge", aliases={"出院", "赛博出院"})


@discharge.handle()
async def _(args: Message = CommandArg()):
    try:
        await hospital_service.discharge_patient(args.extract_plain_text())
        await discharge.finish("出院成功")
    except ValueError:
        await discharge.finish("病人未入院")
