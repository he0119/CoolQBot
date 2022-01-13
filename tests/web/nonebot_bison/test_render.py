import pytest
from nonebug import App


@pytest.mark.asyncio
@pytest.mark.parametrize("app", [("src.web.nonebot_bison",)], indirect=True)
async def test_render(app: App):
    """测试渲染文字"""
    from src.web.nonebot_bison.utils import Render

    render = Render()
    data = await render.text_to_pic_cqcode("一段文字")
    assert data.type == "image"
    # data = await render.text_to_pic(
    #     "订阅的帐号为：\nrss Python https://devblogs.microsoft.com/python/feed/\nbilibili"
    # )
    # if data:
    #     from PIL import Image
    #     from io import BytesIO

    #     Image.open(BytesIO(data)).show()
