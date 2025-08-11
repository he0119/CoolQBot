"""Alisten 服务器 API 客户端"""

import httpx
from nonebot.log import logger
from pydantic import BaseModel

from .models import AlistenConfig


class User(BaseModel):
    name: str
    email: str | None = None


class PickMusicRequest(BaseModel):
    """点歌请求"""

    houseId: str
    housePwd: str = ""
    user: User
    id: str = ""
    name: str = ""
    source: str = "wy"


class MusicData(BaseModel):
    """音乐数据"""

    name: str
    source: str
    id: str


class SuccessResponse(BaseModel):
    """成功响应"""

    code: str
    message: str
    data: MusicData


class ErrorResponse(BaseModel):
    """错误响应"""

    error: str


class AListenAPI:
    """Alisten API 客户端"""

    async def pick_music(
        self, name: str, source: str, user_name: str, config: AlistenConfig
    ) -> SuccessResponse | ErrorResponse:
        """点歌

        Args:
            name: 音乐名称或搜索关键词
            user_name: 用户昵称
            source: 音乐源 (wy/qq/db)
            config: Alisten 配置

        Returns:
            点歌结果
        """
        request_data = PickMusicRequest(
            houseId=config.house_id,
            housePwd=config.house_password,
            user=User(name=user_name, email=""),
            name=name,
            source=source,
        )

        url = f"{config.server_url}/music/pick"

        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                response = await client.post(
                    url,
                    json=request_data.model_dump(),
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    # 尝试解析成功响应
                    try:
                        success_response = SuccessResponse.model_validate(response.json())
                        return success_response
                    except Exception as e:
                        logger.error(f"解析成功响应失败: {e}")
                        return ErrorResponse(error="响应数据格式错误")
                else:
                    # 处理错误响应
                    try:
                        error_response = ErrorResponse.model_validate(response.json())
                        return error_response
                    except Exception:
                        return ErrorResponse(error=f"服务器错误: {response.status_code}")

        except httpx.TimeoutException:
            logger.error("Alisten API 请求超时")
            return ErrorResponse(error="请求超时，请稍后重试")
        except httpx.RequestError as e:
            logger.error(f"Alisten API 请求失败: {e}")
            return ErrorResponse(error="网络连接失败，请检查 Alisten 服务是否正常运行")
        except Exception as e:
            logger.error(f"Alisten API 未知错误: {e}")
            return ErrorResponse(error="点歌失败，请稍后重试")


# 全局 API 实例
api = AListenAPI()
