from fastapi.testclient import TestClient
import nonebot
from fastapi import FastAPI
from nonebot.adapters.onebot.v11 import Bot, Message

app: FastAPI = nonebot.get_app()

client = TestClient(app)

async def test_bot_health():
    response = client.get("/secret/bot_health")
    assert response.status_code == 500
    
    async with app.test_api() as ctx:
        bot = ctx.create_bot(base=Bot)
        response = client.get("/secret/bot_health")
        assert response.status_code == 200