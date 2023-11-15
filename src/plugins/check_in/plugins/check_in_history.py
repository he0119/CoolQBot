from collections.abc import Sequence
from datetime import datetime, timezone
from io import BytesIO

import matplotlib.pyplot as plt
from nonebot.plugin import PluginMetadata, inherit_supported_adapters
from nonebot_plugin_alconna import (
    Alconna,
    AlconnaMatcher,
    Args,
    Image,
    Match,
    Text,
    on_alconna,
)
from nonebot_plugin_user import UserSession
from sqlalchemy import func, select

from src.utils.annotated import AsyncSession

from ..models import BodyFatRecord, DietaryRecord, FitnessRecord, WeightRecord
from ..utils import get_or_create_user_info

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
    supported_adapters=inherit_supported_adapters(
        "nonebot_plugin_alconna", "nonebot_plugin_user"
    ),
)

history_cmd = on_alconna(Alconna("打卡历史", Args["content?", str]), use_cmd_start=True)


@history_cmd.handle()
async def handle_first_message(matcher: AlconnaMatcher, content: Match[str]):
    if content.available:
        matcher.set_path_arg("content", content.result)


@history_cmd.got_path(
    "content",
    prompt="请问你要查询什么历史呢？请输入 A：健身 B：饮食 C：体重 D：体脂",
)
async def _(
    session: AsyncSession,
    user: UserSession,
    content: str,
):
    content = content.lower()
    if not content:
        await history_cmd.reject("选项不能为空，请重新输入", at_sender=True)

    if content not in ["a", "b", "c", "d"]:
        await history_cmd.reject("选项不正确，请重新输入", at_sender=True)

    match content:
        case "a":
            # 仅获取当月记录
            now = (
                datetime.now()
                .replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                .astimezone(tz=timezone.utc)
                .replace(tzinfo=None)
            )
            fitness_records = (
                await session.scalars(
                    select(FitnessRecord)
                    .where(FitnessRecord.user_id == user.user_id)
                    .where(FitnessRecord.time >= now)
                )
            ).all()
            if not fitness_records:
                await history_cmd.finish("你还没有健身打卡记录哦", at_sender=True)
            msgs = [f"你已成功打卡 {len(fitness_records)} 次，以下是你当月的健身情况哦～："]
            for record in fitness_records:
                msgs.append(f"{record.time.date()} {record.message}")
            await history_cmd.finish("\n".join(msgs), at_sender=True)
        case "b":
            count = (
                await session.execute(
                    select(DietaryRecord.healthy, func.count("*"))
                    .where(DietaryRecord.user_id == user.user_id)
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
                    select(WeightRecord).where(WeightRecord.user_id == user.user_id)
                )
            ).all()
            if not weight_records:
                await history_cmd.finish("你还没有体重记录哦", at_sender=True)

            user_info = await get_or_create_user_info(user, session)
            msg = f"你的目标体重是 {user_info.target_weight or 'NaN'}kg\n"

            image = generate_graph(weight_records)
            await history_cmd.finish(
                Text(msg) + Image(raw=image, mimetype="image/png"),
                at_sender=True,
            )
        case "d":
            body_fat_records = (
                await session.scalars(
                    select(BodyFatRecord).where(BodyFatRecord.user_id == user.user_id)
                )
            ).all()
            if not body_fat_records:
                await history_cmd.finish("你还没有体脂记录哦", at_sender=True)

            user_info = await get_or_create_user_info(user, session)
            msg = f"你的目标体脂是 {user_info.target_body_fat or 'NaN'}%\n"

            image = generate_graph(body_fat_records)
            await history_cmd.finish(
                Text(msg) + Image(raw=image, mimetype="image/png"),
                at_sender=True,
            )


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
    fig.savefig(file, format="png")
    return file.getvalue()
