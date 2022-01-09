import nonebot
from nonebot import require
from nonebot.log import logger

from .config import Config
from .platform import platform_manager
from .plugin_config import plugin_config
from .send import do_send_msgs, send_msgs
from .types import UserSubInfo

scheduler = require("nonebot_plugin_apscheduler").scheduler


async def fetch_and_send(target_type: str):
    config = Config()
    target = config.get_next_target(target_type)
    if not target:
        return
    logger.debug(
        "try to fecth new posts from {}, target: {}".format(target_type, target)
    )
    send_user_list = config.target_user_cache[target_type][target]
    send_userinfo_list = list(
        map(
            lambda user: UserSubInfo(
                user,
                lambda target: config.get_sub_category(
                    target_type, target, user.user_type, user.user
                ),
                lambda target: config.get_sub_tags(
                    target_type, target, user.user_type, user.user
                ),
            ),
            send_user_list,
        )
    )
    bot_list = list(nonebot.get_bots().values())
    bot = bot_list[0] if bot_list else None
    to_send = await platform_manager[target_type].fetch_new_post(
        target, send_userinfo_list
    )
    for user, send_list in to_send:
        for send_post in send_list:
            logger.info("send to {}: {}".format(user, send_post))
            if not bot:
                logger.warning("no bot connected")
            else:
                await send_msgs(
                    bot, user.user, user.user_type, await send_post.generate_messages()
                )


for platform_name, platform in platform_manager.items():
    if platform.schedule_type in ["cron", "interval", "date"]:
        logger.info(
            f"start scheduler for {platform_name} with {platform.schedule_type} {platform.schedule_kw}"
        )
        scheduler.add_job(
            fetch_and_send,
            platform.schedule_type,
            **platform.schedule_kw,
            args=(platform_name,),
        )

if plugin_config.bison_use_queue:
    scheduler.add_job(do_send_msgs, "interval", seconds=0.3, coalesce=True)
