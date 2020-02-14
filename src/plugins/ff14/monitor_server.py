""" 服务器状态监控

监控并自动提示服务器状态变化
"""
import asyncio
from datetime import datetime

from coolqbot import PluginData, bot


class ServerMonitor:
    """ 服务器状态监控 """
    def __init__(self):
        self._data = PluginData('ff14', config=True)
        # 定时任务
        self._job = None
        # 当前状态
        self._status = None

        # 根据配置启动
        if bool(
            int(self._data.get_config('ff14', 'monitor_server_status', '0'))
        ):
            self.enable()

    def enable(self):
        self._job = bot.scheduler.add_job(
            self.monitor_server_status, 'interval', seconds=self.interval
        )
        self._data.set_config('ff14', 'monitor_server_status', '1')

    def disable(self):
        self._job.remove()
        self._data.set_config('ff14', 'monitor_server_status', '0')

    @property
    def is_enabled(self):
        """ 是否启用服务器状态监控 """
        if self._job:
            return True
        else:
            return False

    @property
    def status(self):
        """ 服务器状态

        返回格式化字符串
        """
        status = self._status
        if status:
            resp = f'当前的服务器状态({status["time"].strftime("%Y-%m-%d %H:%M:%S")})'
            for name, is_open in status['data'].items():
                resp += f'\n{name}：{"在线" if is_open else "离线"}'
            return resp
        else:
            return '无数据'

    @property
    def interval(self):
        return int(
            self._data.get_config('ff14', 'monitor_server_interval', '60')
        )

    @staticmethod
    async def is_open(ip, port):
        """ 查询端口是否开启 """
        conn = asyncio.open_connection(ip, port)
        try:
            _reader, writer = await asyncio.wait_for(conn, timeout=1)
            writer.close()
            await writer.wait_closed()
            return True
        except asyncio.TimeoutError:
            return False

    async def monitor_server_status(self):
        """ 监控服务器状态 """
        group_id = bot.get_bot().config.GROUP_ID[0]
        if not self._status:
            self._status = await self.get_server_status()
        else:
            current_status = await self.get_server_status()
            if self._status['data'] == current_status['data']:
                pass
            else:
                await bot.get_bot().send_msg(
                    message_type='group',
                    group_id=group_id,
                    message=self.status
                )
            self._status = current_status

    async def get_server_status(self):
        """ 获取服务器状态 """
        # data = {
        #     '陆行鸟': await self.is_open('109.244.5.5', 54994),
        #     '莫古力': await self.is_open('109.244.5.162', 54994),
        #     '猫小胖': await self.is_open('116.211.8.5', 54994),
        # }
        data = {
            '猫小胖': await self.is_open('116.211.8.5', 54994),
            '静语庄园': await self.is_open('116.211.8.46', 55022),
        }
        return {'time': datetime.now(), 'data': data}


server_monitor = ServerMonitor()
