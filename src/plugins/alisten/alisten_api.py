"""alisten 服务器 API 客户端"""

import httpx
from nonebot.log import logger
from pydantic import BaseModel

from .config import plugin_config


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


class PickMusicResult(BaseModel):
    """点歌结果"""

    success: bool
    message: str
    name: str | None = None
    source: str | None = None
    id: str | None = None


class AListenAPI:
    """alisten API 客户端"""

    async def pick_music(self, name: str, source: str, user_name: str) -> PickMusicResult:
        """点歌

        Args:
            name: 音乐名称或搜索关键词
            user_name: 用户昵称
            source: 音乐源 (wy/qq/db)

        Returns:
            点歌结果
        """
        request_data = PickMusicRequest(
            houseId=plugin_config.alisten_house_id,
            housePwd=plugin_config.alisten_house_password,
            user=User(name=user_name, email=""),
            name=name,
            source=source,
        )

        url = f"{plugin_config.alisten_server_url}/music/pick"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=request_data.model_dump(),
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    if "error" in data:
                        return PickMusicResult(
                            success=False,
                            message=data["error"],
                        )
                    else:
                        return PickMusicResult(
                            success=True,
                            message=data.get("message", "点歌成功"),
                            name=data.get("data", {}).get("name"),
                            source=data.get("data", {}).get("source"),
                            id=data.get("data", {}).get("id"),
                        )
                else:
                    # 处理错误响应
                    try:
                        error_data = response.json()
                        error_message = error_data.get("error", f"服务器错误: {response.status_code}")
                    except Exception:
                        error_message = f"服务器错误: {response.status_code}"

                    return PickMusicResult(
                        success=False,
                        message=error_message,
                    )

        except httpx.TimeoutException:
            logger.error("alisten API 请求超时")
            return PickMusicResult(
                success=False,
                message="请求超时，请稍后重试",
            )
        except httpx.RequestError as e:
            logger.error(f"alisten API 请求失败: {e}")
            return PickMusicResult(
                success=False,
                message="网络连接失败，请检查 alisten 服务是否正常运行",
            )
        except Exception as e:
            logger.error(f"alisten API 未知错误: {e}")
            return PickMusicResult(
                success=False,
                message="点歌失败，请稍后重试",
            )


# 全局 API 实例
api = AListenAPI()
