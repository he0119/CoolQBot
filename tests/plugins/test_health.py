from typing import TYPE_CHECKING

import nonebot
import pytest
from fastapi.testclient import TestClient
from nonebot.adapters.onebot.v11 import Bot
from nonebug import App

if TYPE_CHECKING:
    from fastapi import FastAPI


@pytest.fixture
def client(app: App):
    fastapi_app: FastAPI = nonebot.get_app()

    return TestClient(fastapi_app)


async def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200


async def test_bot_health(app: App, client: TestClient):
    async with app.test_api() as ctx:
        bot = ctx.create_bot(base=Bot)

        response = client.get("/secret/bot_health")
        assert response.status_code == 200

        response = client.get("/secret/bot_health", params={"bot_id": bot.self_id})
        assert response.status_code == 200

        response = client.get("/secret/bot_health", params={"bot_id": "unknown"})
        assert response.status_code == 500


async def test_bot_health_no_bot(client: TestClient):
    response = client.get("/secret/bot_health")
    assert response.status_code == 500
