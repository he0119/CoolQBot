import hashlib
from collections.abc import Sequence

from nonebot_plugin_orm import get_session
from sqlalchemy import func, select

from .model import Bihua
from .utils import get_image_path


class BihuaService:
    """壁画服务类"""

    async def add_bihua(self, user_id: int, session_id: str, name: str, image_data: bytes) -> None:
        """添加壁画"""
        # 计算图片hash值
        image_hash = hashlib.md5(image_data).hexdigest()

        async with get_session() as session:
            # 检查是否已经存在相同hash的壁画
            statement = select(Bihua).where(Bihua.image_hash == image_hash, Bihua.session_id == session_id)
            results = await session.scalars(statement)
            existing_bihua = results.first()

            if existing_bihua is not None:
                raise ValueError("相同的壁画已经存在")

            image_path = get_image_path(session_id, image_hash)
            image_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存图片到本地
            with open(image_path, "wb") as f:
                f.write(image_data)

            bihua = Bihua(
                user_id=user_id,
                session_id=session_id,
                name=name,
                image_hash=image_hash,
            )
            session.add(bihua)
            await session.commit()

    async def get_bihua_by_name(self, name: str, session_id: str) -> Bihua | None:
        """根据名称获取壁画"""
        async with get_session() as session:
            statement = select(Bihua).where(Bihua.name == name, Bihua.session_id == session_id)
            results = await session.scalars(statement)
            return results.first()

    async def search_bihua(self, keyword: str, session_id: str) -> Sequence[Bihua]:
        """搜索壁画"""
        async with get_session() as session:
            statement = select(Bihua).where(Bihua.name.contains(keyword), Bihua.session_id == session_id)
            results = await session.scalars(statement)
            return results.all()

    async def get_all_bihua(self, session_id: str) -> Sequence[Bihua]:
        """获取群组所有壁画"""
        async with get_session() as session:
            statement = select(Bihua).where(Bihua.session_id == session_id)
            results = await session.scalars(statement)
            return results.all()

    async def delete_bihua(self, name: str, session_id: str) -> None:
        """删除壁画"""
        async with get_session() as session:
            statement = select(Bihua).where(Bihua.name == name, Bihua.session_id == session_id)
            results = await session.scalars(statement)
            bihua = results.first()

            if bihua is None:
                raise ValueError("壁画不存在")

            # 删除本地文件
            image_path = bihua.image_path()
            if image_path.exists():
                image_path.unlink()

            await session.delete(bihua)
            await session.commit()

    async def get_user_bihua_count(self, session_id: str) -> Sequence[tuple[int, int]]:
        """统计用户收藏的壁画数量"""
        async with get_session() as session:
            statement = (
                select(Bihua.user_id, func.count(Bihua.user_id))
                .group_by(Bihua.user_id)
                .where(Bihua.session_id == session_id)
            )
            results = (await session.execute(statement)).all()
            return [(row[0], row[1]) for row in results]
