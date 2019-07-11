""" 记录数据
"""
from datetime import datetime, timedelta

from coolqbot import PluginData, bot


def get_history_pkl_name(dt):
    time_str = dt.strftime('%Y-%m')
    return time_str


DATA = PluginData('recorder')


class Recorder:
    def __init__(self, data=None):
        self._name = 'recorder'

        # 运行数据
        self._last_message_on = {
            group_id: datetime.now()
            for group_id in bot.get_bot().config.GROUP_ID
        }
        self._msg_send_time = {}
        self._repeat_list = {}
        self._msg_number_list = {}

        # 酷Q 状态
        self.start_time = datetime.now()
        self.coolq_status = False
        # 是否需要发送问好
        self.send_hello = False

        self._load_data(data)

    def message_number(self, x: int, group_id: int):
        """ 返回 x 分钟内的消息条数，并清除之前的消息记录
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

    def get_repeat_list(self, group_id: int):
        """ 获取指定群整个月的复读记录
        """
        if group_id not in self._repeat_list:
            return {}
        return self._merge_list(self._repeat_list[group_id])

    def get_msg_number_list(self, group_id: int):
        """ 获取指定群整个月的消息数量记录
        """
        if group_id not in self._msg_number_list:
            return {}
        return self._merge_list(self._msg_number_list[group_id])

    def get_repeat_list_by_day(self, day, group_id: int):
        """ 获取指定群某一天的复读记录
        """
        if group_id not in self._repeat_list:
            return {}
        if day in self._repeat_list[group_id]:
            return self._repeat_list[group_id][day]
        return {}

    def get_msg_number_list_by_day(self, day, group_id: int):
        """ 获取指定群某一天的消息数量记录
        """
        if group_id not in self._msg_number_list:
            return {}
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
        if group_id not in self._msg_send_time:
            self._msg_send_time[group_id] = []
        self._msg_send_time[group_id].append(time)

    def get_last_message_on(self, group_id: int):
        if group_id not in self._last_message_on:
            return datetime.now()
        return self._last_message_on[group_id]

    def reset_last_message_on(self, group_id: int):
        self._last_message_on[group_id] = datetime.now()

    def _add_to_list(self, recrod_list, qq, group_id: int):
        """ 添加数据进列表
        """
        if group_id not in recrod_list:
            recrod_list[group_id] = {}

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

    def _load_data(self, data):
        """ 加载数据
        """
        if not data:
            try:
                data = DATA.load_pkl(self._name)
            except FileNotFoundError:
                bot.logger.error('recorder.pkl does not exist!')
        if data:
            self.last_message_on = data['last_message_on']
            self._msg_send_time = data['msg_send_time']
            self._repeat_list = data['repeat_list']
            self._msg_number_list = data['msg_number_list']

    def save_data(self):
        """ 保存数据
        """
        DATA.save_pkl(self.get_data(), self._name)

    def get_data(self, history=False):
        """ 如果是 `history` 插件需要的话，不保存一些数据
        """
        if history:
            return {
                'last_message_on': None,
                'msg_send_time': [],
                'repeat_list': self._repeat_list,
                'msg_number_list': self._msg_number_list
            }
        return {
            'last_message_on': self.last_message_on,
            'msg_send_time': self._msg_send_time,
            'repeat_list': self._repeat_list,
            'msg_number_list': self._msg_number_list
        }

    def clear_data(self):
        self._msg_send_time = {}
        self._repeat_list = {}
        self._msg_number_list = {}


recorder = Recorder()


@bot.scheduler.scheduled_job('interval', minutes=1, id='save_recorder')
async def save_recorder():
    """ 每隔一分钟保存一次数据
    """
    # 保存数据前先清理 msg_send_time 列表
    for group_id in bot.get_bot().config.GROUP_ID:
        recorder.message_number(10, group_id)

    recorder.save_data()
