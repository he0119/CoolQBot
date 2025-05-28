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
            {"status": "error", "message": f"Failed to get bot: {e!s}"},
            status_code=500,
        )


# https://github.com/encode/starlette/issues/864
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:  # pragma: no cover
        # complete query string (so parameter and other value included)
        args = record.args
        if not isinstance(args, tuple) or len(args) < 3 or not isinstance(args[2], str):
            # if args is not a tuple or does not have enough elements,
            # we assume it's not a health check request
            return True

        query_string = args[2]

        if query_string.startswith("/health"):
            return False
        if query_string.startswith("/secret/bot_health"):
            return False
        # 顺便过滤掉 prometheus 的 metrics 请求
        if query_string.startswith("/secret/metrics"):
            return False

        return True


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())
