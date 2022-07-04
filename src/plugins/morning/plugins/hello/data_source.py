from datetime import datetime


def get_first_connect_message():
    """根据当前时间返回对应消息"""
    hour = datetime.now().hour

    if hour > 18 or hour < 6:
        return "晚上好呀！"

    if hour > 13:
        return "下午好呀！"

    if hour > 11:
        return "中午好呀！"

    return "早上好呀！"
