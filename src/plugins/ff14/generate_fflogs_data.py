import asyncio
import sys

sys.path.append(".")

import json
from pathlib import Path

import nonebot

nonebot.init()
nonebot.load_plugin("nonebot_plugin_alconna")

from src.plugins.ff14.plugins.ff14_fflogs.api import fflogs
from src.plugins.ff14.plugins.ff14_fflogs.models import Encounter, Zones

DATA_FILE = Path(__file__).parent / "fflogs_data.json"


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


def get_difficulty(zone: Zones, encounter: Encounter):
    """副本难度难度

    绝本的难度是 101

    零式副本的难度是 101，普通的则是 100

    极神也是 100
    """
    # 绝本是 101
    if zone.name.startswith("Ultimates"):
        return 101

    return 100


async def update_boss(data):
    bosses = {
        (boss["zone"], boss["encounter"], boss["difficulty"]): boss
        for boss in data["boss"]
    }

    zones = await fflogs.zones()
    for zone in zones:
        for encounter in zone.encounters:
            difficulty = get_difficulty(zone, encounter)
            if (zone.id, encounter.id, difficulty) not in bosses:
                data["boss"].append(
                    {
                        "name": f"{zone.name} {encounter.name}",
                        "nicknames": [encounter.name],
                        "zone": zone.id,
                        "encounter": encounter.id,
                        "difficulty": difficulty,
                    }
                )


async def main():
    with DATA_FILE.open("r", encoding="utf-8") as f:
        fflogs_data = json.load(f)

    await updata_job(fflogs_data)
    await update_boss(fflogs_data)

    fflogs_data["job"] = sorted(fflogs_data["job"], key=lambda x: x["spec"])
    fflogs_data["boss"] = sorted(
        fflogs_data["boss"], key=lambda x: (x["zone"], x["encounter"], x["difficulty"])
    )

    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(fflogs_data, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    asyncio.run(main())
