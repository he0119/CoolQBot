""" 赛博查房 """
from typing import cast

from nonebot import CommandGroup
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText, CommandArg, Depends
from nonebot.permission import SUPERUSER, USER
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from src.utils.helpers import get_nikcname

from .data_source import Hospital

__plugin_meta__ = PluginMetadata(
    name="赛博医院",
    description="管理病人与记录病人的病情",
    usage="查看入院病人列表\n/查房\n查房并记录病情\n/查房 @病人\n病人入院\n/入院 @病人\n病人出院\n/出院 @病人\n查看病历\n/病历 @病人",
)

hospital_service = Hospital()

hospital = CommandGroup("hospital", permission=GROUP_OWNER | GROUP_ADMIN | SUPERUSER)

room_cmd = hospital.command("room", aliases={"查房", "赛博查房"})


async def user_id(args: Message = CommandArg()) -> str | None:
    if at_message := args["at"]:
        at_message = at_message[0]
        at_message = cast(MessageSegment, at_message)
        return at_message.data["qq"]


@room_cmd.permission_updater
async def _(matcher: Matcher, user_id: str = Arg(), group_id: str = Arg()):
    if user_id and group_id:
        return USER(f"group_{group_id}_{user_id}")
    return matcher.permission


@room_cmd.handle()
async def _(
    bot: Bot,
    event: GroupMessageEvent,
    state: T_State,
    user_id: str | None = Depends(user_id),
):
    group_id = str(event.group_id)

    if user_id:
        state["at"] = MessageSegment.at(user_id)
        state["user_id"] = user_id
        state["group_id"] = group_id
        patient = await hospital_service.get_patient(
            state["user_id"], state["group_id"]
        )
        if not patient:
            await room_cmd.finish(state["at"] + " 未入院")
    else:
        patients = await hospital_service.get_patients(group_id)
        if not patients:
            await room_cmd.finish("当前没有住院病人")

        patient_infos = []
        for patient in patients:
            nikcname = await get_nikcname(int(patient.user_id), event.group_id, bot)
            patient_infos.append(
                f"{nikcname} 入院时间：{patient.admitted_at:%Y-%m-%d %H:%M}"
            )

        await room_cmd.finish("\n".join(patient_infos))


@room_cmd.got("content", prompt=Message.template("{at}请问你现在有什么不适吗？"))
async def _(user_id: str = Arg(), group_id: str = Arg(), content: str = ArgPlainText()):
    await hospital_service.add_record(user_id, group_id, content)
    await room_cmd.finish("记录成功", at_sender=True)


admit_cmd = hospital.command("admit", aliases={"入院", "赛博入院"})


@admit_cmd.handle()
async def _(event: GroupMessageEvent, user_id: str | None = Depends(user_id)):
    if not user_id:
        await admit_cmd.finish("请 @ 需要入院的病人")

    try:
        await hospital_service.admit_patient(user_id, str(event.group_id))
        await admit_cmd.finish(MessageSegment.at(user_id) + "入院成功")
    except ValueError:
        await admit_cmd.finish(MessageSegment.at(user_id) + "已入院")


discharge_cmd = hospital.command("discharge", aliases={"出院", "赛博出院"})


@discharge_cmd.handle()
async def _(event: GroupMessageEvent, user_id: str | None = Depends(user_id)):
    if not user_id:
        await discharge_cmd.finish("请 @ 需要出院的病人")

    try:
        await hospital_service.discharge_patient(user_id, str(event.group_id))
        await discharge_cmd.finish(MessageSegment.at(user_id) + "出院成功")
    except ValueError:
        await discharge_cmd.finish(MessageSegment.at(user_id) + "未入院")


record_cmd = hospital.command("record", aliases={"病历", "赛博病历"})


@record_cmd.handle()
async def _(event: GroupMessageEvent, user_id: str | None = Depends(user_id)):
    if not user_id:
        await discharge_cmd.finish("请 @ 需要查看记录的病人")

    try:
        records = await hospital_service.get_records(user_id, str(event.group_id))
    except ValueError:
        await record_cmd.finish(MessageSegment.at(user_id) + "未入院")
    if not records:
        await record_cmd.finish(MessageSegment.at(user_id) + "暂时没有记录")

    msg = MessageSegment.at(user_id) + "\n"
    await record_cmd.finish(
        msg
        + "\n".join(
            f"{record.time:%Y-%m-%d %H:%M} {record.content}" for record in records
        )
    )
