""" nonebot-hk-reporter

修改自 https://github.com/felinae98/nonebot-hk-reporter
"""
from nonebot import CommandGroup, logger
from nonebot.adapters import Bot, Event
from nonebot.adapters.cqhttp import GroupMessageEvent
from nonebot.adapters.cqhttp.message import Message
from nonebot.typing import T_State

from .config import Config
from .platform import check_sub_target, platform_manager
from .scheduler import fetch_and_send
from .types import Target
from .utils import parse_text

common_platform = [p.platform_name for p in \
        filter(lambda platform: platform.enabled and platform.is_common,
            platform_manager.values())
    ]

sub = CommandGroup('sub', block=True)

#region 添加订阅
add_sub_cmd = sub.command('add', aliases={'添加订阅'})
add_sub_cmd.__doc__ = """
sub.add 添加订阅

订阅

/添加订阅
"""


@add_sub_cmd.handle()
async def init_promote(bot: Bot, event: GroupMessageEvent, state: T_State):
    state['_prompt'] = '请输入想要订阅的平台，目前支持：\n' + \
            ''.join(['{}：{}\n'.format(platform_name, platform_manager[platform_name].name) \
                    for platform_name in common_platform]) + \
            '要查看全部平台请输入："全部"'


async def parse_platform(bot: Bot, event: Event, state: T_State) -> None:
    platform = str(event.get_message()).strip()
    if platform == '全部':
        message = '全部平台\n' + \
            '\n'.join(['{}：{}'.format(platform_name, platform.name) \
                    for platform_name, platform in platform_manager.items()])
        await add_sub_cmd.reject(message)
    elif platform in platform_manager:
        state['platform'] = platform
    else:
        await add_sub_cmd.reject('平台输入错误')


@add_sub_cmd.got('platform', '{_prompt}', parse_platform)
@add_sub_cmd.handle()
async def init_id(bot: Bot, event: GroupMessageEvent, state: T_State):
    if platform_manager[state['platform']].has_target:
        state['_prompt'] = '请输入订阅用户的 ID'
    else:
        state['id'] = 'default'
        state['name'] = await platform_manager[state['platform']
                                               ].get_target_name(Target(''))


async def parse_id(bot: Bot, event: Event, state: T_State):
    target = str(event.get_message()).strip()
    name = await check_sub_target(state['platform'], target)
    if not name:
        await add_sub_cmd.reject('ID 输入错误')
    state['id'] = target
    state['name'] = name


@add_sub_cmd.got('id', '{_prompt}', parse_id)
@add_sub_cmd.handle()
async def init_cat(bot: Bot, event: GroupMessageEvent, state: T_State):
    if not platform_manager[state['platform']].categories:
        state['cats'] = []
        return
    state['_prompt'] = '请输入要订阅的类别，以空格分隔，支持的类别有：{}'.format('，'.join(
        list(platform_manager[state['platform']].categories.values())))


async def parser_cats(bot: Bot, event: Event, state: T_State):
    res = []
    for cat in str(event.get_message()).strip().split():
        if cat not in platform_manager[state['platform']].reverse_category:
            await add_sub_cmd.reject('不支持 {}'.format(cat))
        res.append(platform_manager[state['platform']].reverse_category[cat])
    state['cats'] = res


@add_sub_cmd.got('cats', '{_prompt}', parser_cats)
@add_sub_cmd.handle()
async def init_tag(bot: Bot, event: GroupMessageEvent, state: T_State):
    if not platform_manager[state['platform']].enable_tag:
        state['tags'] = []
        return
    state['_prompt'] = '请输入要订阅的标签，订阅所有标签输入"全部标签"'


async def parser_tags(bot: Bot, event: Event, state: T_State):
    if str(event.get_message()).strip() == '全部标签':
        state['tags'] = []
    else:
        state['tags'] = str(event.get_message()).strip().split()


@add_sub_cmd.got('tags', '{_prompt}', parser_tags)
@add_sub_cmd.handle()
async def add_sub_process(bot: Bot, event: GroupMessageEvent, state: T_State):
    config = Config()
    config.add_subscribe(state.get('_user_id') or event.group_id,
                         user_type='group',
                         target=state['id'],
                         target_name=state['name'],
                         target_type=state['platform'],
                         cats=state.get('cats', []),
                         tags=state.get('tags', []))
    await add_sub_cmd.finish('添加 {} 成功'.format(state['name']))


#endregion
#region 查询订阅
query_sub_cmd = sub.command('query', aliases={'查询订阅'})
query_sub_cmd.__doc__ = """
sub.query 查询订阅

订阅

/查询订阅
"""


@query_sub_cmd.handle()
async def _(bot: Bot, event: GroupMessageEvent, state: T_State):
    config: Config = Config()
    sub_list = config.list_subscribe(
        state.get('_user_id') or event.group_id, "group")
    res = '订阅的帐号为：\n'
    for sub in sub_list:
        res += '{} {} {}'.format(sub['target_type'], sub['target_name'],
                                 sub['target'])
        platform = platform_manager[sub['target_type']]
        if platform.categories:
            res += ' [{}]'.format(', '.join(
                map(lambda x: platform.categories[x], sub['cats'])))
        if platform.enable_tag:
            res += ' {}'.format(', '.join(sub['tags']))
        res += '\n'
    # send_msgs(bot, event.group_id, 'group', [await parse_text(res)])
    await query_sub_cmd.finish(Message(await parse_text(res)))


#endregion
#region 删除订阅
del_sub_cmd = sub.command('del', aliases={'删除订阅'})
del_sub_cmd.__doc__ = """
sub.del 删除订阅

订阅

/删除订阅
"""


@del_sub_cmd.handle()
async def send_list(bot: Bot, event: GroupMessageEvent, state: T_State):
    config: Config = Config()
    sub_list = config.list_subscribe(event.group_id, "group")
    res = '订阅的帐号为：\n'
    state['sub_table'] = {}
    for index, sub in enumerate(sub_list, 1):
        state['sub_table'][index] = {
            'target_type': sub['target_type'],
            'target': sub['target']
        }
        res += '{} {} {} {}\n'.format(index, sub['target_type'],
                                      sub['target_name'], sub['target'])
        platform = platform_manager[sub['target_type']]
        if platform.categories:
            res += ' [{}]'.format(', '.join(
                map(lambda x: platform.categories[x], sub['cats'])))
        if platform.enable_tag:
            res += ' {}'.format(', '.join(sub['tags']))
        res += '\n'
    res += '请输入要删除的订阅的序号'
    await bot.send(event=event, message=Message(await parse_text(res)))


@del_sub_cmd.receive()
async def do_del(bot, event: GroupMessageEvent, state: T_State):
    try:
        index = int(str(event.get_message()).strip())
        config = Config()
        config.del_subscribe(event.group_id, 'group',
                             **state['sub_table'][index])
    except Exception as e:
        logger.warning(e)
        await del_sub_cmd.reject('删除错误')
    else:
        await del_sub_cmd.finish('删除成功')


#endregion
