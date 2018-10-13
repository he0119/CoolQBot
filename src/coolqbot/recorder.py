'''记录数据'''
import pickle
from datetime import datetime, timedelta

from coolqbot.bot import bot
from coolqbot.config import RECORDER_FILE_PATH
from coolqbot.utils import scheduler


class Recorder(object):
    def __init__(self):
        self.last_message_on = datetime.utcnow()
        self.msg_send_time = []
        self.repeat_list = {}
        self.msg_number_list = {}

    def message_number(self, x):
        '''返回x分钟内的消息条数，并清除之前的消息记录'''
        times = self.msg_send_time
        now = datetime.utcnow()
        for i in range(len(times)):
            if times[i] > now - timedelta(minutes=x):
                self.msg_send_time = self.msg_send_time[i:]
                bot.logger.debug(len(self.msg_send_time))
                return len(self.msg_send_time)
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
            self.last_message_on = data['last_message_on']
            self.msg_send_time = data['msg_send_time']
            self.repeat_list = data['repeat_list']
            self.msg_number_list = data['msg_number_list']

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
            with path.open('rb') as f:
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

recorder = Recorder()

recorder.load_data(RECORDER_FILE_PATH)

# TODO:增加每月1日清除上约数据功能
#      增加查询历史记录功能(/history)


@scheduler.scheduled_job('interval', minutes=1)
async def save_recorder():
    '''每隔一分钟保存一次数据'''
    recorder.save_pkl(RECORDER_FILE_PATH)
