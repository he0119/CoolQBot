from pathlib import Path

import nonebot_plugin_localstore as store

# 获取本地存储目录
DATA_DIR = store.get_plugin_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_image_path(group_id: str, image_hash: str) -> Path:
    """根据 hash 和 群组ID 获取图片路径"""
    return DATA_DIR / group_id / f"{image_hash}"
