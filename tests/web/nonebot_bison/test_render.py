from io import BytesIO

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
