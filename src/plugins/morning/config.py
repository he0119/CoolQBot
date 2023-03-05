from datetime import time

from pydantic import BaseSettings


class Config(BaseSettings, extra="ignore"):
    # 每日早安
    morning_time: time = time(7, 30, 0)
