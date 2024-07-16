import logging

import nonebot
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app: FastAPI = nonebot.get_app()


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok"}, status_code=200)


@app.get("/secret/bot_health")
async def bot_check(bot_id: str | None = None):
    try:
        nonebot.get_bot(bot_id)
        return JSONResponse({"status": "ok"}, status_code=200)
    except Exception as e:
        return JSONResponse(
            {"status": "error", "message": f"Failed to get bot: {str(e)}"},
            status_code=500,
        )


# https://github.com/encode/starlette/issues/864
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # complete query string (so parameter and other value included)
        query_string: str = record.args[2]  # type: ignore

        if query_string.startswith("/health"):
            return False
        if query_string.startswith("/secret/bot_health"):
            return False

        return True


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
