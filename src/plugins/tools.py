""" 一些小工具
"""
from nonebot import CommandSession

def to_number(arg: str, session: CommandSession):
    """ 转换成数字
    """
    if arg.isdigit():
        return int(arg)
    else:
        session.pause('请输入数字，不然我没法理解呢！')
