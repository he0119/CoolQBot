'''记录数据'''
import pickle
from datetime import datetime, timedelta

from coolqbot.bot import bot
from coolqbot.config import HISTORY_DIR_PATH, RECORDER_FILE_PATH
from coolqbot.utils import get_history_pkl_name, scheduler


class Recorder(object):
    def __init__(self, path=None):
        self.last_message_on = datetime.utcnow()
        self.msg_send_time = []
        self.repeat_list = {}
        self.msg_number_list = {}
        if path:
            self.load_data(path)

    def message_number(self, x):
        '''返回x分钟内的消息条数，并清除之前的消息记录'''
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

    def load_data(self, path):
        data = None
        if path.exists():
            data = self.load_pkl(path)
        if data:
            try:
                self.last_message_on = data['last_message_on']
                self.msg_send_time = data['msg_send_time']
                self.repeat_list = data['repeat_list']
                self.msg_number_list = data['msg_number_list']
            except TypeError:
                self.last_message_on = data.last_message_on
                self.msg_send_time = data.msg_send_time
                self.repeat_list = data.repeat_list
                self.msg_number_list = data.msg_number_list

    def save_pkl(self, path):
        data = self.get_data()
        try:
            with path.open(mode='wb') as f:
                pickle.dump(data, f)
                bot.logger.debug('记录保存成功')
        except Exception as e:
            bot.logger.error(f'记录保存失败，原因是{e}')

    def load_pkl(self, path):
        try:
            with path.open(mode='rb') as f:
                data = pickle.load(f)
                bot.logger.debug('记录加载成功')
                return data
        except Exception as e:
            bot.logger.error(f'记录加载失败，原因是{e}')
            return None

    def get_data(self):
        return {'last_message_on': self.last_message_on,
                'msg_send_time': self.msg_send_time,
                'repeat_list': self.repeat_list,
                'msg_number_list': self.msg_number_list}

    def clear_data(self):
        self.msg_send_time = []
        self.repeat_list = {}
        self.msg_number_list = {}


recorder = Recorder(RECORDER_FILE_PATH)


@scheduler.scheduled_job('cron', day=1, hour=0, minute=0, second=0)
async def clear_data():
    '''每个月最后一分钟保存记录于历史记录文件夹，并重置记录'''
    # 保存数据到历史文件夹
    date = datetime.now() - timedelta(hours=1)
    recorder.save_pkl(HISTORY_DIR_PATH / f'{get_history_pkl_name(date)}.pkl')
    # 清除现有数据
    recorder.clear_data()
    bot.logger.info('记录清除完成')


@scheduler.scheduled_job('interval', minutes=1)
async def save_recorder():
    '''每隔一分钟保存一次数据'''
    recorder.save_pkl(RECORDER_FILE_PATH)
