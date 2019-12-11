""" 一些数据

副本与职业数据
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

# (zone, encounter, difficulty): [nicknames]
boss_list = {
    (28, 1045, 100): ['提坦妮雅歼殛战', '缇坦妮雅', '妖精', '极妖精', '妖灵王', '妖精王', '老婆', '10王'],
    (28, 1046, 100): ['无瑕灵君歼殛战', '无瑕灵君', '肥宅', '极肥宅', '全能王'],
    (28, 1049, 100): ['哈迪斯歼殛战', '哈迪斯', '老公'],
    (29, 65, 100): ['伊甸希望乐园 觉醒之章1', 'E1', 'e1'],
    (29, 66, 100): ['伊甸希望乐园 觉醒之章2', 'E2', 'e2'],
    (29, 67, 100): ['伊甸希望乐园 觉醒之章3', 'E3', 'e3'],
    (29, 68, 100): ['伊甸希望乐园 觉醒之章4', 'E4', 'e4'],
    (29, 65, 0):   ['伊甸零式希望乐园 觉醒之章1', 'E1S', 'e1s', 'E1s', 'e1S'],
    (29, 66, 0):   ['伊甸零式希望乐园 觉醒之章2', 'E2S', 'e2s', 'E2s', 'e2S'],
    (29, 67, 0):   ['伊甸零式希望乐园 觉醒之章3', 'E3S', 'e3s', 'E3s', 'e3S'],
    (29, 68, 0):   ['伊甸零式希望乐园 觉醒之章4', 'E4S', 'e4s', 'E4s', 'e4S'],
} # yapf: disable

# spec: [nicknames]
job_list = {
    1:  ['占星术士', '占星'],
    2:  ['吟游诗人', '诗人'],
    3:  ['黑魔法师', '黑魔', '伏地魔', '永动机'],
    4:  ['暗黑骑士', '黑骑', '暗骑', 'DK'],
    5:  ['龙骑士', '龙骑', '躺尸龙', '擦炮工'],
    6:  ['机工士', '机工'],
    7:  ['武僧', '扫地僧', '猴子', '和尚'],
    8:  ['忍者', '兔忍', '火影'],
    9:  ['骑士', '圣骑', '奶骑'],
    10: ['学者', '小仙女', '死炎法师'],
    11: ['召唤师', '召唤'],
    12: ['战士', '战爹'],
    13: ['白魔法师', '白魔', '白膜', '投石机'],
    14: ['赤魔法师', '赤魔', '吃馍', '红色治疗'],
    15: ['武士', '侍'],
    16: ['舞者', '舞娘'],
    17: ['绝枪战士', '绝枪', '枪刃', '枪决战士'],
} # yapf: disable

@dataclass
class BossInfo:
    """ BOSS 的信息 """
    name: str
    zone: int
    encounter: int
    difficulty: int


@dataclass
class JobInfo:
    """ 职业的信息 """
    name: str
    spec: int


def get_boss_info_by_nickname(name: str) -> Optional[BossInfo]:
    """ 根据昵称获取 BOSS 的相关信息

    返回包含 `name`, `zone`, `encounter`, `difficulty` 信息的数据类
    """
    for (zone, encounter, difficulty), nicknames in boss_list.items():
        if name in nicknames:
            return BossInfo(nicknames[0], zone, encounter, difficulty)
    return None


def get_bosses_info() -> List[BossInfo]:
    """ 获取所有 BOSS 的相关信息 """
    boss_info = []
    for (zone, encounter, difficulty), nicknames in boss_list.items():
        boss_info.append(BossInfo(nicknames[0], zone, encounter, difficulty))
    return boss_info


def get_job_info_by_nickname(name: str) -> Optional[JobInfo]:
    """ 根据昵称获取职业的相关信息

    返回包含 `name`, `spec` 信息的数据类
    """
    for spec, nicknames in job_list.items():
        if name in nicknames:
            return JobInfo(nicknames[0], spec)
    return None


def get_jobs_info() -> List[JobInfo]:
    """ 获取所有职业的相关信息 """
    job_info = []
    for spec, nicknames in job_list.items():
        job_info.append(JobInfo(nicknames[0], spec))
    return job_info
