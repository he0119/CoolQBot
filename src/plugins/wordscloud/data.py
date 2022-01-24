from pathlib import Path
from typing import Optional

import jieba
from PIL.Image import Image
from wordcloud import WordCloud

from .model import Message

font_path = Path(__file__).parent / "SimHei.ttf"
stopwords_path = Path(__file__).parent / "stopwords.txt"
with stopwords_path.open("r", encoding="utf8") as f:
    stopwords = [word.strip() for word in f.readlines()]


async def get_wordcloud(messages: list[Message]) -> Optional[Image]:
    words = []
    # 过滤掉命令
    msgs = " ".join([m.message for m in messages if not m.message.startswith("/")])
    # 分词
    words = jieba.lcut(msgs, cut_all=True)
    txt = "\n".join(words)
    try:
        wordcloud = WordCloud(font_path=str(font_path), stopwords=stopwords)
        image = wordcloud.generate(txt).to_image()
        return image
    except ValueError:
        pass
