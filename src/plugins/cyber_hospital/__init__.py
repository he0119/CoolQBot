"""赛博查房"""

from nonebot.matcher import Matcher
from nonebot.params import ArgPlainText
from nonebot.permission import Permission
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot.typing import T_State
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaMatcher,
    Args,
    At,
    Text,
    UniMessage,
    on_alconna,
)
from nonebot_plugin_user import User, UserSession, get_user, get_user_by_id

from src.utils.helpers import admin_permission

from . import migrations
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
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna", "nonebot_plugin_user"
    ),
    extra={"orm_version_location": migrations},
)

hospital_service = Hospital()

rounds_cmd = on_alconna(
    Alconna("查房", Args["at?", At]["content?", str]),
    permission=admin_permission(),
    use_cmd_start=True,
)


def ensure_user(uid: int):
    async def checker(user: User):
        if user.id == uid:
            return True
        return False

    return Permission(checker)


@rounds_cmd.permission_updater
async def _(matcher: Matcher, at_uid: int | None = None):
    if at_uid:
        return ensure_user(at_uid)
    return matcher.permission


@rounds_cmd.handle()
async def _(
    state: T_State,
    matcher: AlconnaMatcher,
    user: UserSession,
    at: At | None = None,
    content: str | None = None,
):
    if at:
        if content:
            state["content"] = UniMessage(content)
        at_user = await get_user(user.platform, at.target)
        patient = await hospital_service.get_admitted_patient(at_user.id)
        if not patient:
            await rounds_cmd.finish(at + Text(" 未入院"))

        matcher.set_path_arg("at_uid", at_user.id)
        matcher.set_path_arg("at_pid", at.target)
    else:
        patients = await hospital_service.get_admitted_patients(user.group_session_id)
        if not patients:
            await rounds_cmd.finish("当前没有住院病人")

        patient_infos = []
        for patient in patients:
            # TODO: get nickname
            # nikcname = await get_nickname(bot, patient.user_id, patient.group_id)
            nickname = (await get_user_by_id(patient.user_id)).name
            patient_info = f"{nickname} 入院时间：{patient.admitted_at:%Y-%m-%d %H:%M}"
            latest_record = patient.records[-1] if patient.records else None
            if latest_record:
                patient_info += f" 上次查房时间：{latest_record.time:%Y-%m-%d %H:%M}"
            else:
                patient_info += " 上次查房时间：无"
            patient_infos.append(patient_info)

        await rounds_cmd.finish("\n".join(patient_infos))


@rounds_cmd.got("content", prompt=UniMessage.template("{at}请问你现在有什么不适吗？"))
async def _(at_uid: int, at_pid: str, content: str = ArgPlainText()):
    at = At("user", at_pid)
    if not content.strip():
        await rounds_cmd.reject(at + Text("症状不能为空，请重新输入"))

    await hospital_service.add_record(at_uid, content)
    await rounds_cmd.finish(at + Text("记录成功"))


admit_cmd = on_alconna(
    Alconna("入院", Args["at?", At]),
    permission=admin_permission(),
    use_cmd_start=True,
)


@admit_cmd.handle()
async def _(user: UserSession, at: At | None = None):
    if not at:
        await admit_cmd.finish("请 @ 需要入院的病人")

    try:
        at_user = await get_user(user.platform, at.target)
        await hospital_service.admit_patient(at_user.id, user.group_session_id)
        await admit_cmd.finish(at + Text("入院成功"))
    except ValueError:
        await admit_cmd.finish(at + Text("已入院"))


discharge_cmd = on_alconna(
    Alconna("出院", Args["at?", At]),
    permission=admin_permission(),
    use_cmd_start=True,
)


@discharge_cmd.handle()
async def _(user: UserSession, at: At | None = None):
    if not at:
        await discharge_cmd.finish("请 @ 需要出院的病人")

    try:
        at_user = await get_user(user.platform, at.target)
        await hospital_service.discharge_patient(at_user.id, user.group_session_id)
        await discharge_cmd.finish(at + Text("出院成功"))
    except ValueError:
        await discharge_cmd.finish(at + Text("未入院"))


record_cmd = on_alconna(
    Alconna("病历", Args["at?", At]),
    permission=admin_permission(),
    use_cmd_start=True,
)


@record_cmd.handle()
async def _(user: UserSession, at: At | None = None):
    if not at:
        await discharge_cmd.finish("请 @ 需要查看记录的病人")

    try:
        at_user = await get_user(user.platform, at.target)
        records = await hospital_service.get_records(at_user.id, user.group_session_id)
    except ValueError:
        await record_cmd.finish(at + Text("未入院"))
    if not records:
        await record_cmd.finish(at + Text("暂时没有记录"))

    msg = at + Text("\n")
    await record_cmd.finish(
        msg
        + "\n".join(
            f"{record.time:%Y-%m-%d %H:%M} {record.content}" for record in records
        )
    )


history_cmd = on_alconna(
    Alconna("入院记录", Args["at?", At]),
    permission=admin_permission(),
    use_cmd_start=True,
)


@history_cmd.handle()
async def _(user: UserSession, at: At | None = None):
    if not at:
        patients = await hospital_service.patient_count(user.group_session_id)
        if not patients:
            await history_cmd.finish("没有住院病人")

        patient_infos = []
        for user_id, count in patients:
            nickname = (await get_user_by_id(user_id)).name
            patient_infos.append(f"{nickname} 入院次数：{count}")
        await history_cmd.finish("\n".join(patient_infos))

    at_user = await get_user(user.platform, at.target)
    patients = await hospital_service.get_patient(at_user.id, user.group_session_id)
    if not patients:
        await history_cmd.finish(UniMessage(at) + "从未入院")

    patient_info = []
    for patient in patients:
        info = f"入院时间：{patient.admitted_at:%Y-%m-%d %H:%M}"
        if patient.discharged_at:
            info += f" 出院时间：{patient.discharged_at:%Y-%m-%d %H:%M}"
        else:
            info += " 出院时间：未出院"
        patient_info.append(info)

    await history_cmd.finish(UniMessage(at) + "\n".join(patient_info))
