""" 自主禁言插件
"""
from jieba import posseg
from nonebot import (
    CommandSession, IntentCommand, NLPSession, on_command, on_natural_language
)


@on_command('ban', aliases=('禁言'), only_to_me=False)
async def ban(session: CommandSession):
    duration = session.get('duration', prompt='你想被禁言多少分钟呢？')
    duration = duration * 60

    # 如果在群里发送，则在当前群禁言/解除
    if session.ctx['message_type'] == 'group':
        role = session.ctx['sender']['role']
        group_id = session.ctx['group_id']
        if role == 'member':
            await session.bot.set_group_ban(
                group_id=session.ctx['group_id'],
                user_id=session.ctx['sender']['user_id'],
                duration=duration
            )
        elif role == 'admin':
            owner_id = await get_owner(group_id, session.bot)
            await session.send(
                f'你是管理员，我没法禁言你，不过我可以帮你[CQ:at,qq={owner_id}]~', at_sender=True
            )
        elif role == 'owner':
            await session.send(f'你是群主，你开心就好。', at_sender=True)

    # 如果私聊的话，则在所有小誓约支持的群禁言/解除
    elif session.ctx['message_type'] == 'private':
        for group_id in session.bot.config.GROUP_ID:
            await session.bot.set_group_ban(
                group_id=group_id,
                user_id=session.ctx['sender']['user_id'],
                duration=duration
            )


@ban.args_parser
async def _(session: CommandSession):
    # 去掉消息首尾的空白符
    stripped_arg = session.current_arg_text.strip()

    if session.is_first_run:
        # 该命令第一次运行（第一次进入命令会话）
        if stripped_arg and stripped_arg.isdigit():
            session.state['duration'] = int(stripped_arg)
        return

    if not stripped_arg:
        session.pause('禁言时间不能为空呢，请重新输入')

    # 检查输入参数是不是数字
    if stripped_arg.isdigit():
        session.state[session.current_key] = int(stripped_arg)
    else:
        session.pause('请只输入数字，不然我没法理解呢！')


@on_natural_language(keywords={'禁言'})
async def _(session: NLPSession):
    # 去掉消息首尾的空白符
    stripped_msg = session.msg_text.strip()
    # 对消息进行分词和词性标注
    words = posseg.lcut(stripped_msg)

    duration = None
    # 遍历 posseg.lcut 返回的列表
    for word in words:
        # 每个元素是一个 pair 对象，包含 word 和 flag 两个属性，分别表示词和词性
        if word.flag == 'm':
            # m 表示数量
            duration = word.word

    # 返回意图命令，前两个参数必填，分别表示置信度和意图命令名
    return IntentCommand(90.0, 'ban', current_arg=duration or '')


async def get_owner(group_id: int, bot):
    """ 获取群主 QQ 号
    """
    group_info = await bot._get_group_info(group_id=group_id)
    return group_info['owner_id']
