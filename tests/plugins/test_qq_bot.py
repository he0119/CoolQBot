from typing import TYPE_CHECKING

import nonebot
import pytest
from fastapi.testclient import TestClient
from nonebug import App

if TYPE_CHECKING:
    from fastapi import FastAPI


@pytest.fixture
def client(app: App):
    fastapi_app: FastAPI = nonebot.get_app()

    return TestClient(fastapi_app)


async def test_qq_bot(app: App, client: TestClient):
    async with app.test_api():
        response = client.get("/123456.json")
        assert response.status_code == 200
        assert response.json() == {"bot_appid": 123456}

        # 如果不是配置中的机器人
        response = client.get("/1234561.json")
        assert response.status_code == 404
        assert response.json() == {"detail": "Not Found"}

        # 如果是任意字符串
        response = client.get("/wwwwww.json")
        assert response.status_code == 404
        assert response.json() == {"detail": "Not Found"}
