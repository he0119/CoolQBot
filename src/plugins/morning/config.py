from datetime import time

from pydantic import BaseModel, Extra


class Config(BaseModel, extra=Extra.ignore):
    # 每日早安
    morning_time: time = time(7, 30, 0)
