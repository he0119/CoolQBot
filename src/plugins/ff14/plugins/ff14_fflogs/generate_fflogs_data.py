import asyncio
import re
import sys

sys.path.append(".")

import json
from pathlib import Path

import nonebot

nonebot.init()
nonebot.load_plugin("nonebot_plugin_alconna")

from src.plugins.ff14.plugins.ff14_fflogs.api import fflogs
from src.plugins.ff14.plugins.ff14_fflogs.models import Encounter, Partition, Zones

DATA_FILE = Path(__file__).parents[5] / "public" / "fflogs_data.json"
CN_AREA = 2


async def updata_job(data):
    jobs = {job["spec"]: job for job in data["job"]}

    classes = await fflogs.classes()
    for class_ in classes:
        for spec in class_.specs:
            if spec.id not in jobs:
                data["job"].append(
                    {
                        "name": spec.name,
                        "nicknames": [],
                        "spec": spec.id,
                    }
                )


def get_name(zones: Zones, encounter: Encounter):
    """副本名字"""
    # 普通副本直接返回
    if zones.name.startswith("Dungeons"):
        return encounter.name
    return f"{zones.name} {encounter.name}"


def get_difficulty(zone: Zones, encounter: Encounter):
    """副本难度

    绝本的难度是 100

    零式副本的难度是 101，普通的则是 100

    极神也是 100
    """
    # 绝本是 100
    if zone.name.startswith("Ultimates"):
        return 100
    # 零式是 101
    if "Savage" in zone.name:
        return 101

    return 100


def get_ultimate_partitions(zone: Zones) -> list[tuple[int, Partition]]:
    """获取国服标准阵容分区及 FFLogs 使用的分区编号。"""
    return [
        (partition.id or index, partition)
        for index, partition in enumerate(zone.partitions or [], start=1)
        if partition.area == CN_AREA
        and (partition.partition_type == "Standard" or partition.name.startswith("标准阵容构成"))
    ]


def get_version(partition: Partition) -> str | None:
    """获取适合展示的分区版本。"""
    return partition.patch or partition.filtered_name


def get_existing_version(name: str) -> str | None:
    """从旧数据名称中提取版本，用于兼容没有版本信息的冻结分区。"""
    matched = re.search(r"\(([^()]+)\)$", name)
    return matched.group(1) if matched else None


def get_nicknames(name: str, existing: list[dict], default: bool) -> list[str]:
    """保留人工维护的昵称，并补充规范化名称。"""
    nicknames = {name.replace(" ", "-").lower()}
    for boss in existing:
        if boss["name"] == name or (default and get_existing_version(boss["name"]) is None):
            nicknames.update(boss["nicknames"])
    return sorted(nicknames)


def generate_ultimate_bosses(zone: Zones, existing_bosses: list[dict]) -> list[dict]:
    """为一个绝本区域生成所有国服版本。"""
    result = []
    partitions = get_ultimate_partitions(zone)

    for encounter in zone.encounters:
        encounter_existing = [boss for boss in existing_bosses if boss["encounter"] == encounter.id]
        for partition_id, partition in partitions:
            version = get_version(partition)
            if version is None and len(partitions) == 1 and encounter_existing:
                version = get_existing_version(encounter_existing[0]["name"])

            name = f"{encounter.name}({version})" if version else encounter.name
            result.append(
                {
                    "name": name,
                    "nicknames": get_nicknames(name, encounter_existing, bool(partition.default)),
                    "zone": zone.id,
                    "encounter": encounter.id,
                    "difficulty": 100,
                    "partition": partition_id,
                    "version": version,
                    "partition_end": partition.end_time,
                    "partition_frozen": bool(partition.frozen or zone.frozen),
                }
            )

    return result


async def update_boss(data, zones: list[Zones] | None = None):
    zones = zones or await fflogs.zones()
    ultimate_zones = [zone for zone in zones if zone.name.startswith("Ultimates")]
    ultimate_zone_ids = {zone.id for zone in ultimate_zones}
    existing_ultimate_bosses = [boss for boss in data["boss"] if boss["zone"] in ultimate_zone_ids]

    # 绝本数据需要整体重建，避免保留旧的错误难度和缺少 partition 的记录。
    data["boss"] = [boss for boss in data["boss"] if boss["zone"] not in ultimate_zone_ids]
    for zone in ultimate_zones:
        zone_existing = [boss for boss in existing_ultimate_bosses if boss["zone"] == zone.id]
        data["boss"].extend(generate_ultimate_bosses(zone, zone_existing))

    bosses = {
        (boss["zone"], boss["encounter"], boss["difficulty"], boss.get("partition")): boss for boss in data["boss"]
    }

    for zone in zones:
        if zone.id in ultimate_zone_ids:
            continue
        for encounter in zone.encounters:
            name = get_name(zone, encounter)
            difficulty = get_difficulty(zone, encounter)
            if (zone.id, encounter.id, difficulty, None) not in bosses:
                data["boss"].append(
                    {
                        "name": name,
                        "nicknames": [name.replace(" ", "-").lower()],
                        "zone": zone.id,
                        "encounter": encounter.id,
                        "difficulty": difficulty,
                    }
                )


async def main():
    with DATA_FILE.open("r", encoding="utf-8") as f:
        fflogs_data = json.load(f)

    await updata_job(fflogs_data)
    zones = await fflogs.zones()
    await update_boss(fflogs_data, zones)
    fflogs_data["version"] = f"{max(zone.brackets.max for zone in zones):g}"

    fflogs_data["job"] = sorted(fflogs_data["job"], key=lambda x: x["spec"])
    fflogs_data["boss"] = sorted(
        fflogs_data["boss"],
        key=lambda x: (x["zone"], x["encounter"], x["difficulty"], x.get("partition") or 0),
    )

    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(fflogs_data, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
