from nonebot_plugin_orm import get_session
from sqlalchemy import select

from .model import GroupBind


class GroupBindService:
    """群组绑定服务类"""

    async def bind_group(self, session_id: str, bind_id: str) -> None:
        """将群组绑定到目标群组"""
        async with get_session() as session:
            # 检查该群组是否已经绑定到其他群组
            statement = select(GroupBind).where(GroupBind.session_id == session_id)
            existing = await session.scalars(statement)
            if existing.first():
                raise ValueError("该群组已经绑定到其他群组")

            bind_entry = GroupBind(session_id=session_id, bind_id=bind_id)
            session.add(bind_entry)
            await session.commit()

    async def unbind_group(self, session_id: str) -> None:
        """将群组从绑定中移除"""
        async with get_session() as session:
            statement = select(GroupBind).where(GroupBind.session_id == session_id)
            results = await session.scalars(statement)
            bind_entry = results.first()

            if bind_entry is None:
                raise ValueError("该群组未绑定到任何群组")

            await session.delete(bind_entry)
            await session.commit()

    async def get_bind_id(self, session_id: str) -> str:
        """获取绑定的目标群组 ID"""
        async with get_session() as session:
            statement = select(GroupBind.bind_id).where(GroupBind.session_id == session_id)
            result = await session.scalars(statement)
            bind_id = result.first()

            if bind_id is None:
                return session_id  # 如果没有绑定，返回自身的 session_id

            return bind_id

    async def get_bound_session_ids(self, session_id: str) -> list[str]:
        """获取所有绑定到同一目标的 session_id 列表"""
        async with get_session() as session:
            # 先查找当前群组绑定的目标
            statement = select(GroupBind.bind_id).where(GroupBind.session_id == session_id)
            result = await session.scalars(statement)
            bind_id = result.first()

            if bind_id is None:
                # 如果当前群组没有绑定，检查是否有其他群组绑定到当前群组
                statement = select(GroupBind.session_id).where(GroupBind.bind_id == session_id)
                results = await session.scalars(statement)
                bound_session_ids = list(results.all())

                if bound_session_ids:
                    # 如果有其他群组绑定到当前群组，返回包含当前群组的所有群组
                    return [session_id, *bound_session_ids]
                else:
                    # 如果没有绑定关系，只返回自己
                    return [session_id]

            # 获取所有绑定到同一目标的session_id，包括目标本身
            statement = select(GroupBind.session_id).where(GroupBind.bind_id == bind_id)
            results = await session.scalars(statement)
            bound_session_ids = list(results.all())

            # 添加目标群组本身
            return [bind_id, *bound_session_ids]

    async def is_group_bound(self, session_id: str) -> bool:
        """检查群组是否已经绑定"""
        async with get_session() as session:
            statement = select(GroupBind).where(GroupBind.session_id == session_id)
            result = await session.scalars(statement)
            return result.first() is not None
