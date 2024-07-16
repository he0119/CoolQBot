import logging

import nonebot
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app: FastAPI = nonebot.get_app()


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok"}, status_code=200)


# curl https://bot.hehome.xyz/bot_health?bot_id=2835792370
@app.get("/bot_health")
async def bot_check(bot_id: Optional[str] = None):
    try:
        bot = nonebot.get_bot(bot_id)
        return JSONResponse({"status": "ok"}, status_code=200)
    except Exception as e:
        return JSONResponse(
            {
                "status": "error", 
                "message": f"Failed to get bot: {str(e)}"
            },
            status_code=500
        )


# https://github.com/encode/starlette/issues/864
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("/health") == -1


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
