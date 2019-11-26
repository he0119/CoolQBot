""" 一些数据
"""
boss_list = {
    1045: ['缇坦妮雅', '妖精', '极妖精', '妖灵王', '妖精王', '老婆', '10王'],
    1046: ['无瑕灵君', '肥宅', '极肥宅', '全能王'],
    1049: ['哈迪斯', '老公']
} # yapf: disable

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


def get_boss_info(name):
    """ 根据昵称获取 boss 的 ID 同时返回正式名称
    """
    for boss_id, nickname in boss_list.items():
        if name in nickname:
            return boss_id, nickname[0]
    return None, None


def get_job_name(name):
    """ 将中文昵称转换成具体的 ID 同时返回正式名称
    """
    for job_id, nickname in job_list.items():
        if name in nickname:
            return job_id, nickname[0]
    return None, None
