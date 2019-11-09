""" 一些数据
"""
boss_list = {
    (28, 1045): ['缇坦妮雅', '妖精', '极妖精', '妖灵王', '妖精王', '老婆', '10王'],
    (28, 1046): ['无瑕灵君', '肥宅', '极肥宅', '全能王'],
    (28, 1049): ['哈迪斯', '老公']
} # yapf: disable

job_list = {
    'Astrologian': ['占星术士', '占星'],
    'Bard':        ['吟游诗人', '诗人'],
    'BlackMage':   ['黑魔法师', '黑魔', '伏地魔', '永动机'],
    'Dancer':      ['舞者', '舞娘'],
    'DarkKnight':  ['暗黑骑士', '黑骑', '暗骑', 'DK'],
    'Dragoon':     ['龙骑士', '龙骑', '躺尸龙', '擦炮工'],
    'Gunbreaker':  ['绝枪战士', '绝枪', '枪刃', '枪决战士'],
    'Machinist':   ['机工士', '机工'],
    'Monk':        ['武僧', '扫地僧', '猴子', '和尚'],
    'Ninja':       ['忍者', '兔忍', '火影'],
    'Paladin':     ['骑士', '圣骑', '奶骑'],
    'RedMage':     ['赤魔法师', '赤魔', '吃馍', '红色治疗'],
    'Samurai':     ['武士', '侍'],
    'Scholar':     ['学者', '小仙女', '死炎法师'],
    'Summoner':    ['召唤师', '召唤'],
    'Warrior':     ['战士', '战爹'],
    'WhiteMage':   ['白魔法师', '白魔', '白膜', '投石机'],
} # yapf: disable


def get_boss_info(name):
    """ 根据昵称获取 boss 的 bucket 和 id
    """
    for boss, nickname in boss_list.items():
        if name in nickname:
            return boss, nickname[0]
    return (None, None), None


def get_job_name(name):
    """ 将中文称呼转换成英文称呼
    """
    for name_en, nickname in job_list.items():
        if name in nickname:
            return name_en, nickname[0]
    return None, None
