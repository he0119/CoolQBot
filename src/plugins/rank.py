'''复读排行'''
import collections
import re
from operator import itemgetter

from coolqbot.bot import bot
from coolqbot.config import GROUP_ID
from coolqbot.recorder import recorder


@bot.on_message('group', 'private')
async def rank(context):
    match = re.match(r'^\/rank ?(\d*)?', context['message'])
    if match:
        args = match.group(1)
        if args:
            str_data = await get_ranking(recorder.repeat_list, int(args))
        else:
            str_data = await get_ranking(recorder.repeat_list, 3)
        if str_data == '复读排行榜':
            str_data = '暂时还没有人被复读( ´∀`)σ)Д`)'
        return {'reply': str_data, 'at_sender': False}


async def get_ranking(repeat_list, x):
    od = collections.OrderedDict(
        sorted(repeat_list.items(), key=itemgetter(1), reverse=True))
    i = 1
    str_data = '复读排行榜'
    for k, v in od.items():
        msg = await bot.get_group_member_info(group_id=GROUP_ID,user_id=k, no_cache=True)
        if msg['card']:
            name = msg['card']
        else:
            name = msg['nickname']
        str_data += f'\n{name}: {v}次'
        i += 1
        if i > x:
            break
    return str_data
