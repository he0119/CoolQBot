import hashlib
from collections.abc import Sequence

from nonebot_plugin_orm import get_session
from sqlalchemy import func, select

from .model import Bihua


class BihuaService:
    """壁画服务类"""

    async def add_bihua(
        self, user_id: int, group_id: str, name: str, image_data: bytes, image_url: str | None = None
    ) -> None:
        """添加壁画"""
        # 计算图片hash值
        image_hash = hashlib.md5(image_data).hexdigest()

        async with get_session() as session:
            # 检查是否已经存在相同hash的壁画
            statement = select(Bihua).where(Bihua.image_hash == image_hash, Bihua.group_id == group_id)
            results = await session.scalars(statement)
            existing_bihua = results.first()

            if existing_bihua is not None:
                raise ValueError("相同的壁画已经存在")

            bihua = Bihua(
                user_id=user_id,
                group_id=group_id,
                name=name,
                image_hash=image_hash,
                image_url=image_url,
                image_data=image_data,
            )
            session.add(bihua)
            await session.commit()

    async def get_bihua_by_name(self, name: str, group_id: str) -> Bihua | None:
        """根据名称获取壁画"""
        async with get_session() as session:
            statement = select(Bihua).where(Bihua.name == name, Bihua.group_id == group_id)
            results = await session.scalars(statement)
            return results.first()

    async def search_bihua(self, keyword: str, group_id: str) -> Sequence[Bihua]:
        """搜索壁画"""
        async with get_session() as session:
            statement = select(Bihua).where(Bihua.name.contains(keyword), Bihua.group_id == group_id)
            results = await session.scalars(statement)
            return results.all()

    async def get_all_bihua(self, group_id: str) -> Sequence[Bihua]:
        """获取群组所有壁画"""
        async with get_session() as session:
            statement = select(Bihua).where(Bihua.group_id == group_id)
            results = await session.scalars(statement)
            return results.all()

    async def delete_bihua(self, name: str, group_id: str, user_id: int) -> None:
        """删除壁画（只能删除自己收藏的）"""
        async with get_session() as session:
            statement = select(Bihua).where(Bihua.name == name, Bihua.group_id == group_id, Bihua.user_id == user_id)
            results = await session.scalars(statement)
            bihua = results.first()

            if bihua is None:
                raise ValueError("壁画不存在或不是你收藏的")

            await session.delete(bihua)
            await session.commit()

    async def get_user_bihua_count(self, group_id: str) -> Sequence[tuple[int, int]]:
        """统计用户收藏的壁画数量"""
        async with get_session() as session:
            statement = (
                select(Bihua.user_id, func.count(Bihua.user_id))
                .group_by(Bihua.user_id)
                .where(Bihua.group_id == group_id)
            )
            results = (await session.execute(statement)).all()
            return [(row[0], row[1]) for row in results]
