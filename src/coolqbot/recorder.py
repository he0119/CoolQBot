'''记录数据'''
import pickle
from datetime import datetime, timedelta

from coolqbot.bot import bot
from coolqbot.config import RECORDER_FILE_PATH
from coolqbot.utils import scheduler


def save():
    try:
        with open(RECORDER_FILE_PATH, 'wb') as f:
            pickle.dump(recorder, f)
            bot.logger.debug('记录保存成功')
    except Exception as e:
        bot.logger.error(f'记录保存失败，原因是{e}')


def load():
    global recorder
    try:
        with open(RECORDER_FILE_PATH, 'rb') as f:
            recorder = pickle.load(f)
            bot.logger.debug('记录加载成功')
    except Exception as e:
        bot.logger.error(f'记录加载失败，原因是{e}')


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

recorder = Recorder()
load()


@scheduler.scheduled_job('interval', minutes=1)
async def save_recorder():
    '''每隔一分钟保存一次数据'''
    save()
