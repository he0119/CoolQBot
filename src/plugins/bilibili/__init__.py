#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@Author         : richardchien
@Date           : 2020-04-14 21:59:54
@LastEditors    : yanyongyu
@LastEditTime   : 2020-04-14 22:12:11
@Description    : None
@GitHub         : https://github.com/richardchien
"""
__author__ = "richardchien"

from nonebot import CommandGroup

__plugin_name__ = "bilibili"


def __plugin_usage__(target, *args, **kwargs):
    if target == "name":
        return "📺 bilibili番剧"
    else:
        return "📺 bilibili番剧\n\n最近有什么番\n2018年1月有什么番\nJOJO的奇妙冒险更新了没有"


cg = CommandGroup("bilibili_anime")

from . import commands, nlp
