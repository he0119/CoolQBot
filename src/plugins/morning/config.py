from datetime import time

from pydantic import BaseModel


class Config(BaseModel):
    # 每日早安
    morning_time: time = time(7, 30, 0)
