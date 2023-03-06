import nonebot
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app: FastAPI = nonebot.get_app()


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok"}, status_code=200)
