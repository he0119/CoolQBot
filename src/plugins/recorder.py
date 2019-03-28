""" 记录数据
"""
from datetime import datetime, timedelta

from coolqbot.bot import bot
from coolqbot.plugin import PluginData
from coolqbot.utils import get_history_pkl_name, scheduler


class Recorder:
    def __init__(self):
        self._name = 'recorder'

        # 运行数据
        self.last_message_on = datetime.utcnow()
        self.msg_send_time = []
        self.repeat_list = {}
        self.msg_number_list = {}

        # 酷Q状态
        self.start_time = datetime.utcnow()
        self.coolq_status = False
        # 是否需要发送问好
        self.send_hello = False
        self.is_restart = False

        # 初始化插件数据管理
        self._data = PluginData('recorder')

        self._load_data()

    def message_number(self, x):
        """ 返回x分钟内的消息条数，并清除之前的消息记录
        """
        times = self.msg_send_time
        now = datetime.utcnow()
        for i in range(len(times)):
            if times[i] > now - timedelta(minutes=x):
                self.msg_send_time = self.msg_send_time[i:]
                bot.logger.debug(self.msg_send_time)
                bot.logger.debug(len(self.msg_send_time))
                return len(self.msg_send_time)

        # 如果没有满足条件的消息，则清除记录
        self.msg_send_time = []
        bot.logger.debug(self.msg_send_time)
        bot.logger.debug(len(self.msg_send_time))
        return len(self.msg_send_time)

    def add_to_list(self, recrod_list, qq):
        try:
            recrod_list[qq] += 1
        except KeyError:
            recrod_list[qq] = 1

    def _load_data(self):
        data = None
        try:
            data = self._data.load_pkl(self._name)
        except FileNotFoundError:
            bot.logger.error('recorder.pkl does not exist!')
        if data:
            self.last_message_on = data['last_message_on']
            self.msg_send_time = data['msg_send_time']
            self.repeat_list = data['repeat_list']
            self.msg_number_list = data['msg_number_list']

    def save_data(self):
        self._data.save_pkl(self.get_data(), self._name)

    def get_data(self):
        return {'last_message_on': self.last_message_on,
                'msg_send_time': self.msg_send_time,
                'repeat_list': self.repeat_list,
                'msg_number_list': self.msg_number_list}

    def clear_data(self):
        self.msg_send_time = []
        self.repeat_list = {}
        self.msg_number_list = {}


recorder = Recorder()


@scheduler.scheduled_job('interval', minutes=1, id='save_recorder')
async def save_recorder():
    """ 每隔一分钟保存一次数据
    """
    recorder.save_data()
