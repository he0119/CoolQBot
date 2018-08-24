'''复读排行'''
import re
import collections
from operator import itemgetter
from coolqbot.bot import bot
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
        if not str_data:
            str_data = '暂时还没有人被复读( ´∀`)σ)Д`)'
        return {'reply': str_data}

async def get_ranking(repeat_list, x):
    od = collections.OrderedDict(sorted(repeat_list.items(), key=itemgetter(1), reverse=True))
    i = 1
    str_data = ''
    for k, v in od.items():
        msg = await bot.get_stranger_info(user_id=k)
        str_data += f'\n{msg["nickname"]}: {v}'
        i += 1
        if i > x:
            break
    return str_data
