"""从聊天消息中提取发给模型的内容

把当前消息和被回复的消息拆成文字与图片，并标明两者的关系，避免模型混淆。
"""

from nonebot.adapters import Bot, Event
from nonebot.typing import T_State
from nonebot_plugin_alconna import Image, Match, MsgId, UniMessage, image_fetch
from nonebot_plugin_alconna.builtins.extensions.reply import ReplyRecordExtension

from .schemas import ImageContent


async def extract_dialogue_content(
    content: Match[UniMessage],
    msg_id: MsgId,
    ext: ReplyRecordExtension,
    bot: Bot,
    event: Event,
    state: T_State,
) -> tuple[str, list[ImageContent] | None]:
    """分别提取当前消息与被回复消息，并编码其回复关系。"""
    current_message = content.result if content.available else UniMessage()
    reply_message = UniMessage()
    reply = ext.get_reply(msg_id)
    has_reply = reply is not None
    if reply is not None:
        if not reply.msg:
            raise ValueError("上一条消息内容为空")
        raw_reply_message = reply.msg
        if isinstance(raw_reply_message, str):
            raw_reply_message = event.get_message().__class__(raw_reply_message)
        reply_message = UniMessage.of(raw_reply_message, bot=bot)

    current_text = current_message.extract_plain_text().strip()
    replied_text = reply_message.extract_plain_text().strip()
    current_images = current_message.get(Image)
    replied_images = reply_message.get(Image)
    images = await fetch_message_images([*current_images, *replied_images], event, bot, state)

    if has_reply and not current_text and not current_images:
        return replied_text, images or None
    if has_reply:
        text = format_reply_context(
            current_text,
            replied_text,
            current_image_count=len(current_images),
            replied_image_count=len(replied_images),
        )
    else:
        text = current_text
    return text, images or None


def format_reply_context(
    current_text: str,
    replied_text: str,
    *,
    current_image_count: int,
    replied_image_count: int,
) -> str:
    """明确标记回复目标与当前请求，避免模型把结构本身当成待处理数据。"""
    parts = [
        "【用户正在回复或引用的消息】",
        replied_text or "（无文字）",
        "",
        "【用户本次发送的消息】",
        current_text or "（无文字）",
    ]
    if current_image_count or replied_image_count:
        parts.extend(["", "【图片归属】"])
        if current_image_count and replied_image_count:
            parts.append(
                f"随请求提供的前 {current_image_count} 张图片属于用户本次发送的消息，"
                f"后 {replied_image_count} 张属于用户正在回复或引用的消息。"
            )
        elif current_image_count:
            parts.append(f"随请求提供的 {current_image_count} 张图片均属于用户本次发送的消息。")
        else:
            parts.append(f"随请求提供的 {replied_image_count} 张图片均属于用户正在回复或引用的消息。")
    return "\n".join(parts)


async def fetch_message_images(
    image_segments: list[Image],
    event: Event,
    bot: Bot,
    state: T_State,
) -> list[ImageContent]:
    """读取一条消息中的全部图片。"""
    images: list[ImageContent] = []
    for image in image_segments:
        data = await image_fetch(event, bot, state, image)
        if not data:
            raise ValueError("图片读取失败")
        images.append(ImageContent.from_bytes(data))
    return images
