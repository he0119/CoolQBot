from collections.abc import Sequence
from datetime import timezone
from io import BytesIO

import matplotlib.pyplot as plt
from nonebot.adapters.onebot.v11 import Bot as BotV11
from nonebot.adapters.onebot.v11 import MessageSegment as MessageSegmentV11
from nonebot.adapters.onebot.v12 import Bot as BotV12
from nonebot.adapters.onebot.v12 import MessageSegment as MessageSegmentV12
from nonebot.params import Arg, Depends
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
from sqlalchemy import func, select

from src.utils.annotated import AsyncSession, PlainTextArgs, UserInfo
from src.utils.helpers import parse_str

from .. import check_in
from ..helpers import ensure_user
from ..models import BodyFatRecord, DietaryRecord, FitnessRecord, WeightRecord

__plugin_meta__ = PluginMetadata(
    name="打卡历史",
    description="查看打卡历史记录",
    usage="""查看健身历史
/打卡历史 A
查看饮食历史
/打卡历史 B
查看体重历史
/打卡历史 C
查看体脂历史
/打卡历史 D""",
    extra={
        "adapters": ["OneBot V11", "OneBot V12"],
    },
)
history_cmd = check_in.command("history", aliases={"打卡历史"})


@history_cmd.handle()
async def handle_first_message(state: T_State, content: PlainTextArgs):
    state["content"] = content


@history_cmd.got(
    "content",
    prompt="请问你要查询什么历史呢？请输入 A：健身 B：饮食 C：体重 D：体脂",
    parameterless=[Depends(parse_str("content"))],
)
async def _(
    bot: BotV11 | BotV12,
    session: AsyncSession,
    user_info: UserInfo,
    content: str = Arg(),
):
    content = content.lower()
    if not content:
        await history_cmd.reject("选项不能为空，请重新输入", at_sender=True)

    if content not in ["a", "b", "c", "d"]:
        await history_cmd.reject("选项不正确，请重新输入", at_sender=True)

    user = await ensure_user(session, user_info)

    match content:
        case "a":
            weight_records = (
                await session.scalars(
                    select(FitnessRecord).where(FitnessRecord.user == user)
                )
            ).all()
            if not weight_records:
                await history_cmd.finish("你还没有健身打卡记录哦", at_sender=True)
            msgs = [f"你已成功打卡 {len(weight_records)} 次，以下是你当月的健身情况哦～："]
            for record in weight_records:
                msgs.append(f"{record.time.date()} {record.message}")
            await history_cmd.finish("\n".join(msgs), at_sender=True)
        case "b":
            count = (
                await session.execute(
                    select(DietaryRecord.healthy, func.count("*"))
                    .where(DietaryRecord.user == user)
                    .group_by(DietaryRecord.healthy)
                )
            ).all()
            if not count:
                await history_cmd.finish("你还没有饮食打卡记录哦", at_sender=True)

            healthy_count = next(filter(lambda x: x[0], count), (0, 0))[1]
            unhealthy_count = next(filter(lambda x: not x[0], count), (0, 0))[1]
            total_count = healthy_count + unhealthy_count
            msg = f"你已成功打卡 {total_count} 次，其中健康饮食 {healthy_count} 次，不健康饮食 {unhealthy_count} 次"
            await history_cmd.finish(msg, at_sender=True)
        case "c":
            weight_records = (
                await session.scalars(
                    select(WeightRecord).where(WeightRecord.user == user)
                )
            ).all()
            if not weight_records:
                await history_cmd.finish("你还没有体重记录哦", at_sender=True)

            msg = f"你的目标体重是 {user.target_weight or 'NaN'}kg\n"

            image = generate_graph(weight_records)
            if isinstance(bot, BotV11):
                msg += MessageSegmentV11.image(image)
            else:
                file_id = (
                    await bot.upload_file(type="data", data=image, name="weight.png")
                )["file_id"]
                msg += MessageSegmentV12.image(file_id)

            await history_cmd.finish(msg, at_sender=True)
        case "d":
            body_fat_records = (
                await session.scalars(
                    select(BodyFatRecord).where(BodyFatRecord.user == user)
                )
            ).all()
            if not body_fat_records:
                await history_cmd.finish("你还没有体脂记录哦", at_sender=True)

            msg = f"你的目标体脂是 {user.target_body_fat or 'NaN'}%\n"

            image = generate_graph(body_fat_records)
            if isinstance(bot, BotV11):
                msg += MessageSegmentV11.image(image)
            else:
                file_id = (
                    await bot.upload_file(type="data", data=image, name="body_fat.png")
                )["file_id"]
                msg += MessageSegmentV12.image(file_id)

            await history_cmd.finish(msg, at_sender=True)


def generate_graph(records: Sequence[WeightRecord] | Sequence[BodyFatRecord]) -> bytes:
    if isinstance(records[0], WeightRecord):
        title = "Weight History"
        xlabel = "time"
        ylabel = "weight (kg)"
    else:
        title = "Body Fat History"
        xlabel = "time"
        ylabel = "body fat (%)"

    data = {
        record.time.replace(tzinfo=timezone.utc).astimezone(): record.weight
        if isinstance(record, WeightRecord)
        else record.body_fat
        for record in records
    }
    fig, ax = plt.subplots(constrained_layout=True)

    ax.plot(data.keys(), data.values())
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.xaxis_date()

    fig.autofmt_xdate()

    file = BytesIO()
    fig.savefig(file)
    return file.getvalue()
