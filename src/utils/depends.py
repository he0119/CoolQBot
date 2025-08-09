from nonebot.adapters import Message
from nonebot.params import CommandArg


async def get_plaintext_args(args: Message = CommandArg()) -> str | None:
    """获取纯文本命令参数"""
    if content := args["text"]:
        if message_str := content.extract_plain_text().strip():
            return message_str
