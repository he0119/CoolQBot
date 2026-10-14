"""渲染一次 Markdown，确认机器人能连上浏览器。

Python 的 playwright 包和浏览器容器的版本必须完全一致，差一点 Playwright 就会
拒绝连接（报 428 和 "Playwright version mismatch"）。这个脚本把那条链路真正
跑一遍：

    docker exec <容器> uv run /app/scripts/render_smoke_test.py

注意 htmlrender 是 NoneBot 插件，必须先 init 再加载插件，不能直接 import，
否则会报 "NoneBot has not been initialized"。

渲染成功退出码为 0，失败非 0，供 CI 判断。
"""

import asyncio
import sys


def _load_htmlrender():
    """按 bot.py 的顺序初始化 NoneBot，再取出 render_markdown。"""
    import nonebot

    nonebot.init()
    nonebot.load_plugin("nonebot_plugin_htmlrender")

    from nonebot_plugin_htmlrender import render_markdown

    return render_markdown


async def main() -> int:
    render_markdown = _load_htmlrender()

    image = await render_markdown("# render smoke test")

    # htmlrender 0.8 返回的是 RenderedImage，不是裸 bytes。
    data = getattr(image, "data", None)
    if not data or data[:8] != b"\x89PNG\r\n\x1a\n":
        print(f"渲染没有返回 PNG（拿到 {type(image).__name__}）", file=sys.stderr)
        return 1
    print(f"渲染成功，{len(data)} 字节")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
