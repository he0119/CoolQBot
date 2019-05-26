""" 复读插件
"""
import re
import secrets
from datetime import datetime, timedelta

from coolqbot import MessageType, bot

from .recorder import recorder


class Repeat(bot.Plugin):
    def __init__(self, bot, *events):
        super().__init__(bot, *events, config=True)
        # 复读概率
        self._repeat_rate = int(
            self.data.config_get('bot', 'repeat_rate', fallback='10'))
        # 复读间隔
        self._repeat_interval = int(
            self.data.config_get('bot', 'repeat_interval', fallback='1'))

    async def on_message(self, context):
        """ 人类本质
        """
        if self._is_repeat(context):
            return {'reply': context['message'], 'at_sender': False}

    def _is_repeat(self, context):
        # 只复读指定群内消息
        if context['group_id'] != bot.config['GROUP_ID']:
            return False

        # 不要复读指令
        match = re.match(r'^\/', context['message'])
        if match:
            return False

        # 不要复读@机器人的消息
        match = re.search(fr'\[CQ:at,qq={context["self_id"]}\]',
                          context['message'])
        if match:
            return False

        # 记录群内发送消息数量和时间
        now = datetime.now()
        recorder.add_msg_send_time(now)

        # 如果不是PRO版本则不复读纯图片
        match = re.search(r'\[CQ:image[^\]]+\]$', context['message'])
        if match and not bot.config['IS_COOLQ_PRO']:
            return False

        # 不要复读应用消息
        if context['sender']['user_id'] == 1000000:
            return False

        # 不要复读签到，分享
        match = re.match(r'^\[CQ:(sign|share).+\]', context['message'])
        if match:
            return False

        # 不要复读过长的文字
        new_msg = re.sub(r'\[CQ:[^\]]+\]', '', context['raw_message'])
        if len(new_msg) > 28:
            return False

        # 复读之后1分钟之内不再复读
        time = recorder.last_message_on
        if datetime.now() < time + timedelta(minutes=self._repeat_interval):
            return False

        repeat_rate = self._repeat_rate
        # 当10分钟内发送消息数量大于30条时，降低复读概率
        # 因为排行榜需要固定概率来展示欧非，暂时取消
        # if recorder.message_number(10) > 30:
        #     bot.logger.info('Repeat rate changed!')
        #     repeat_rate = 5

        # 记录每个人发送消息数量
        recorder.add_msg_number_list(context['user_id'])

        # 按照设定概率复读
        random = secrets.SystemRandom()
        rand = random.randint(1, 100)
        bot.logger.info(rand)
        if rand > repeat_rate:
            return False

        # 记录复读时间
        recorder.last_message_on = now

        # 记录复读次数
        recorder.add_repeat_list(context['user_id'])

        return True


bot.plugin_manager.register(Repeat(bot, MessageType.Group))


class RepeatSign(bot.Plugin):
    async def on_message(self, context):
        """ 复读签到(电脑上没法看手机签到内容)
        """
        if context['group_id'] == bot.config['GROUP_ID']:
            match = re.match(r'^\[CQ:sign(.+)\]$', context['message'])
            if match:
                title = re.findall(r'title=(\w+\s?\w+)', context['message'])
                return {'reply': f'今天的运势是{title[0]}'}


bot.plugin_manager.register(RepeatSign(bot, MessageType.Group))
