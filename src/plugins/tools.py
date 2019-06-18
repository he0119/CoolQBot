""" 一些小工具
"""
from nonebot import CommandSession

def to_number(arg: str, session: CommandSession):
    """ 转换成数字
    """
    try:
        return int(arg)
    except:
        session.pause('请输入数字，不然我没法理解呢！')

