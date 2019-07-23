""" 记录数据

如果遇到老版本数据，则自动升级
"""
from datetime import datetime, timedelta

from coolqbot import PluginData, bot

VERSION = '1'
DATA = PluginData('recorder')


class Recorder:
    def __init__(self, name: str, data: PluginData):
        self._name = name
        self._data = data

        # 初始化运行数据
        self.init_data()

        # 机器人状态
        # 启动时间
        self.start_time = datetime.now()
        # 酷Q 状态
        self.coolq_status = False
        # 是否需要发送问好
        self.send_hello = False

        self._load_data()

    def message_number(self, x: int, group_id: int):
        """ 返回指定群 x 分钟内的消息条数，并清除之前的消息记录
        """
        times = self._msg_send_time[group_id]
        now = datetime.now()
        for i in range(len(times)):
            if times[i] > now - timedelta(minutes=x):
                times = times[i:]
                return len(times)

        # 如果没有满足条件的消息，则清除记录
        times = []
        return len(times)

    def repeat_list(self, group_id: int):
        """ 获取指定群整个月的复读记录
        """
        return self._merge_list(self._repeat_list[group_id])

    def msg_number_list(self, group_id: int):
        """ 获取指定群整个月的消息数量记录
        """
        return self._merge_list(self._msg_number_list[group_id])

    def repeat_list_by_day(self, day, group_id: int):
        """ 获取指定群某一天的复读记录
        """
        if day in self._repeat_list[group_id]:
            return self._repeat_list[group_id][day]
        return {}

    def msg_number_list_by_day(self, day, group_id: int):
        """ 获取指定群某一天的消息数量记录
        """
        if day in self._msg_number_list[group_id]:
            return self._msg_number_list[group_id][day]
        return {}

    def add_repeat_list(self, qq, group_id: int):
        """ 该 QQ 号在指定群的复读记录，加一
        """
        self._add_to_list(self._repeat_list, qq, group_id)

    def add_msg_number_list(self, qq, group_id: int):
        """ 该 QQ 号在指定群的消息数量记录，加一
        """
        self._add_to_list(self._msg_number_list, qq, group_id)

    def add_msg_send_time(self, time, group_id: int):
        """ 将这个时间加入到指定群的消息发送时间列表中
        """
        self._msg_send_time[group_id].append(time)

    def last_message_on(self, group_id: int):
        return self._last_message_on[group_id]

    def reset_last_message_on(self, group_id: int):
        self._last_message_on[group_id] = datetime.now()

    def _add_to_list(self, recrod_list, qq, group_id: int):
        """ 添加数据进列表
        """
        day = datetime.now().day
        if day not in recrod_list[group_id]:
            recrod_list[group_id][day] = {}
        try:
            recrod_list[group_id][day][qq] += 1
        except KeyError:
            recrod_list[group_id][day][qq] = 1

    def _merge_list(self, recrod_list):
        """ 合并词典中按天数存储的数据
        """
        new_list = {}
        for day_list in recrod_list:
            for qq in recrod_list[day_list]:
                if qq in new_list:
                    new_list[qq] += recrod_list[day_list][qq]
                else:
                    new_list[qq] = recrod_list[day_list][qq]
        return new_list

    def _load_data(self):
        """ 加载数据
        """
        if not self._data.exists(f'{self._name}.pkl'):
            bot.logger.error(f'{self._name}.pkl does not exist!')
            return

        data = self._data.load_pkl(self._name)

        # 如果是老版本格式的数据则先升级在加载
        # 默认使用配置中第一个群来升级老数据
        if 'version' not in data or data['version'] != VERSION:
            bot.logger.info('发现旧版本数据，正在升级数据')
            data = update(data, bot.get_bot().config.GROUP_ID[0])
            self._data.save_pkl(self._name)
            bot.logger.info('升级数据成功')

        # 加载数据
        self._last_message_on = data['last_message_on']
        self._msg_send_time = data['msg_send_time']
        self._repeat_list = data['repeat_list']
        self._msg_number_list = data['msg_number_list']

        # 如果群列表新加了群，则补充所需的数据
        for group_id in bot.get_bot().config.GROUP_ID:
            if group_id not in self._last_message_on:
                self._last_message_on[group_id] = datetime.now()

            if group_id not in self._msg_send_time:
                self._msg_send_time[group_id] = []

            if group_id not in self._repeat_list:
                self._repeat_list[group_id] = {}

            if group_id not in self._msg_number_list:
                self._msg_number_list[group_id] = {}

    def save_data(self):
        """ 保存数据
        """
        self._data.save_pkl(self.get_data(), self._name)

    def get_data(self):
        """ 获取当前数据

        并附带上数据的版本
        """
        return {
            'version': VERSION,
            'last_message_on': self._last_message_on,
            'msg_send_time': self._msg_send_time,
            'repeat_list': self._repeat_list,
            'msg_number_list': self._msg_number_list
        }

    def init_data(self):
        """ 初始化数据
        """
        self._last_message_on = {
            group_id: datetime.now()
            for group_id in bot.get_bot().config.GROUP_ID
        }
        self._msg_send_time = {
            group_id: []
            for group_id in bot.get_bot().config.GROUP_ID
        }
        self._repeat_list = {
            group_id: {}
            for group_id in bot.get_bot().config.GROUP_ID
        }
        self._msg_number_list = {
            group_id: {}
            for group_id in bot.get_bot().config.GROUP_ID
        }


recorder = Recorder('recorder', DATA)


@bot.scheduler.scheduled_job('interval', minutes=1, id='save_recorder')
async def save_recorder():
    """ 每隔一分钟保存一次数据
    """
    # 保存数据前先清理 msg_send_time 列表，仅保留最近 10 分钟的数据
    for group_id in bot.get_bot().config.GROUP_ID:
        recorder.message_number(10, group_id)

    recorder.save_data()


def get_history_pkl_name(dt):
    time_str = dt.strftime('%Y-%m')
    return time_str


def update(data: list, group_id: int):
    """ 升级脚本

    升级 0.8.1 及以前版本的 recorder 数据。
    """
    # 判断是那种类型的数据
    if isinstance(list(data.values())[0], int):
        return update_old_1(data, group_id)
    else:
        return update_old_2(data, group_id)


def update_old_1(data: list, group_id: int):
    """ 升级 0.7.0 之前版本的数据
    """
    new_data = {}
    # 添加版本信息
    new_data['version'] = VERSION

    # 升级 last_message_on
    new_data['last_message_on'] = {}
    new_data['last_message_on'][group_id] = data['last_message_on']

    # 升级 msg_send_time
    new_data['msg_send_time'] = {}
    new_data['msg_send_time'][group_id] = []

    # 升级 repeat_list
    new_data['repeat_list'] = {}
    new_data['repeat_list'][group_id] = data['repeat_list']

    # 升级 msg_number_list
    new_data['msg_number_list'] = {}
    new_data['msg_number_list'][group_id] = data['msg_number_list']
    return new_data


def update_old_2(data: list, group_id: int):
    """ 升级 0.7.0-0.8.1 版本的 recorder 数据
    """
    new_data = {}
    # 添加版本信息
    new_data['version'] = VERSION

    # 升级 last_message_on
    new_data['last_message_on'] = {}
    new_data['last_message_on'][group_id] = data['last_message_on']

    # 升级 msg_send_time
    new_data['msg_send_time'] = {}
    new_data['msg_send_time'][group_id] = []

    # 升级 repeat_list
    new_data['repeat_list'] = {}
    new_data['repeat_list'][group_id] = data['repeat_list']

    # 升级 msg_number_list
    new_data['msg_number_list'] = {}
    new_data['msg_number_list'][group_id] = data['msg_number_list']
    return new_data
