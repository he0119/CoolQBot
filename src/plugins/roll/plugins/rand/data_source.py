""" 掷骰子 """
import re
from random import randint


def get_rand(input_str: str) -> str:
    """掷骰子"""
    str_data = ""
    probability = re.match(r"^.+(可能性|几率|概率)$", input_str)
    if probability:
        str_data += input_str
        str_data += "是 "
        str_data += str(randint(0, 100))
        str_data += "%"
    else:
        str_data += "你的点数是 "
        str_data += str(randint(0, 100))

    return str_data
