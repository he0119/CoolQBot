""" 赛博查房 """
from nonebot import CommandGroup
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent, Message, MessageSegment
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.matcher import Matcher
from nonebot.params import Arg, ArgPlainText, CommandArg, Depends
from nonebot.permission import SUPERUSER, USER
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State

from src.utils.annotated import OptionalMentionedUser
from src.utils.helpers import get_nickname

from .data_source import Hospital

__plugin_meta__ = PluginMetadata(
    name="赛博医院",
    description="管理病人与记录病人的病情",
    usage="""查看入院病人列表
/查房
查房并记录病情
/查房 @病人
直接记录病情
/查房 @病人 症状
病人入院
/入院 @病人
病人出院
/出院 @病人
查看病历
/病历 @病人
查看所有人入院次数，或指定人出入院时间
/入院记录
/入院记录 @病人""",
    supported_adapters={"~onebot.v11"},
)

hospital_service = Hospital()

hospital = CommandGroup(
    "hospital", permission=GROUP_OWNER | GROUP_ADMIN | SUPERUSER, block=True
)

rounds_cmd = hospital.command("rounds", aliases={"查房", "赛博查房"})


async def get_content(args: Message = CommandArg()) -> Message | None:
    if content := args["text"]:
        if content.extract_plain_text().strip():
            return content


@rounds_cmd.permission_updater
async def _(matcher: Matcher, user_id: str = Arg(), group_id: str = Arg()):
    if user_id and group_id:
        return USER(f"group_{group_id}_{user_id}")
    return matcher.permission


@rounds_cmd.handle()
async def _(
    bot: Bot,
    event: GroupMessageEvent,
    state: T_State,
    mentioned_user: OptionalMentionedUser,
    content: Message | None = Depends(get_content),
):
    group_id = str(event.group_id)

    if mentioned_user:
        if content:
            state["content"] = content
        state["at"] = mentioned_user.segment
        state["user_id"] = mentioned_user.id
        state["group_id"] = group_id
        patient = await hospital_service.get_admitted_patient(
            state["user_id"], state["group_id"]
        )
        if not patient:
            await rounds_cmd.finish(state["at"] + " 未入院")
    else:
        patients = await hospital_service.get_admitted_patients(group_id)
        if not patients:
            await rounds_cmd.finish("当前没有住院病人")

        patient_infos = []
        for patient in patients:
            nikcname = await get_nickname(bot, patient.user_id, patient.group_id)
            patient_info = f"{nikcname} 入院时间：{patient.admitted_at:%Y-%m-%d %H:%M}"
            latest_record = patient.records[-1] if patient.records else None
            if latest_record:
                patient_info += f" 上次查房时间：{latest_record.time:%Y-%m-%d %H:%M}"
            else:
                patient_info += " 上次查房时间：无"
            patient_infos.append(patient_info)

        await rounds_cmd.finish("\n".join(patient_infos))


@rounds_cmd.got("content", prompt=Message.template("{at}请问你现在有什么不适吗？"))
async def _(user_id: str = Arg(), group_id: str = Arg(), content: str = ArgPlainText()):
    if not content.strip():
        await rounds_cmd.reject(MessageSegment.at(user_id) + "症状不能为空，请重新输入")

    await hospital_service.add_record(user_id, group_id, content)
    await rounds_cmd.finish(MessageSegment.at(user_id) + "记录成功")


admit_cmd = hospital.command("admit", aliases={"入院", "赛博入院"})


@admit_cmd.handle()
async def _(
    event: GroupMessageEvent,
    mentioned_user: OptionalMentionedUser,
):
    if not mentioned_user:
        await admit_cmd.finish("请 @ 需要入院的病人")

    try:
        await hospital_service.admit_patient(mentioned_user.id, str(event.group_id))
        await admit_cmd.finish(mentioned_user.segment + "入院成功")
    except ValueError:
        await admit_cmd.finish(mentioned_user.segment + "已入院")


discharge_cmd = hospital.command("discharge", aliases={"出院", "赛博出院"})


@discharge_cmd.handle()
async def _(
    event: GroupMessageEvent,
    mentioned_user: OptionalMentionedUser,
):
    if not mentioned_user:
        await discharge_cmd.finish("请 @ 需要出院的病人")

    try:
        await hospital_service.discharge_patient(mentioned_user.id, str(event.group_id))
        await discharge_cmd.finish(mentioned_user.segment + "出院成功")
    except ValueError:
        await discharge_cmd.finish(mentioned_user.segment + "未入院")


record_cmd = hospital.command("record", aliases={"病历", "赛博病历"})


@record_cmd.handle()
async def _(
    event: GroupMessageEvent,
    mentioned_user: OptionalMentionedUser,
):
    if not mentioned_user:
        await discharge_cmd.finish("请 @ 需要查看记录的病人")

    try:
        records = await hospital_service.get_records(
            mentioned_user.id, str(event.group_id)
        )
    except ValueError:
        await record_cmd.finish(mentioned_user.segment + "未入院")
    if not records:
        await record_cmd.finish(mentioned_user.segment + "暂时没有记录")

    msg = mentioned_user.segment + "\n"
    await record_cmd.finish(
        msg
        + "\n".join(
            f"{record.time:%Y-%m-%d %H:%M} {record.content}" for record in records
        )
    )


history_cmd = hospital.command("history", aliases={"入院记录", "赛博入院记录"})


@history_cmd.handle()
async def _(
    bot: Bot,
    event: GroupMessageEvent,
    mentioned_user: OptionalMentionedUser,
):
    if not mentioned_user:
        patients = await hospital_service.patient_count(str(event.group_id))
        if not patients:
            await history_cmd.finish("没有住院病人")

        patient_infos = []
        for user_id, count in patients:
            nikcname = await get_nickname(
                bot,
                user_id,
                str(event.group_id),
            )
            patient_infos.append(f"{nikcname} 入院次数：{count}")
        await history_cmd.finish("\n".join(patient_infos))

    patients = await hospital_service.get_patient(
        mentioned_user.id, str(event.group_id)
    )
    if not patients:
        await history_cmd.finish(mentioned_user.segment + "从未入院")

    patient_info = []
    for patient in patients:
        info = f"入院时间：{patient.admitted_at:%Y-%m-%d %H:%M}"
        if patient.discharged_at:
            info += f" 出院时间：{patient.discharged_at:%Y-%m-%d %H:%M}"
        else:
            info += " 出院时间：未出院"
        patient_info.append(info)

    await history_cmd.finish(mentioned_user.segment + "\n".join(patient_info))
