from config import config
from database.redis_db import redis_db
from database.sqlite_db import sqlite_db


class MarryService:

    def __init__(self):
        # 存储待确认的求婚请求: {(chat_id, from_id, to_id): True}
        self._pending: dict[tuple[int, int, int], bool] = {}

    async def propose(self, chat_id: int, from_id: int, to_id: int) -> dict:
        """求婚"""
        if from_id == to_id:
            return {"ok": False, "message": "不能和自己结婚！"}

        # 检查双方是否已婚
        from_marry = await redis_db.get_marry(chat_id, from_id)
        if from_marry is not None:
            return {"ok": False, "message": "你已经结婚了！先离婚再追求别人吧～"}

        to_marry = await redis_db.get_marry(chat_id, to_id)
        if to_marry is not None:
            return {"ok": False, "message": "对方已经结婚了！"}

        # 检查积分
        cost = config.MARRY_COST
        points = await redis_db.get_points(chat_id, from_id)
        if points < cost:
            return {"ok": False, "message": f"积分不足！结婚需要 {cost} 积分，你只有 {points}"}

        # 记录待确认
        self._pending[(chat_id, from_id, to_id)] = True

        return {"ok": True, "cost": cost, "from_id": from_id, "to_id": to_id}

    async def accept(self, chat_id: int, from_id: int, to_id: int) -> dict:
        """接受求婚"""
        key = (chat_id, from_id, to_id)
        if key not in self._pending:
            return {"ok": False, "message": "没有待确认的求婚请求！"}

        # 再次检查
        from_marry = await redis_db.get_marry(chat_id, from_id)
        to_marry = await redis_db.get_marry(chat_id, to_id)

        if from_marry is not None or to_marry is not None:
            del self._pending[key]
            return {"ok": False, "message": "其中一方已经结婚了！"}

        # 扣除积分
        cost = config.MARRY_COST
        points = await redis_db.get_points(chat_id, from_id)
        if points < cost:
            del self._pending[key]
            return {"ok": False, "message": "积分不足！"}

        await redis_db.add_points(chat_id, from_id, -cost)

        # 建立婚姻关系（双向）
        await redis_db.set_marry(chat_id, from_id, to_id)
        await redis_db.set_marry(chat_id, to_id, from_id)

        # 记录到SQLite
        await sqlite_db.add_marriage(chat_id, from_id, to_id)

        # 清除待确认
        del self._pending[key]

        return {"ok": True, "cost": cost}

    async def reject(self, chat_id: int, from_id: int, to_id: int) -> dict:
        """拒绝求婚"""
        key = (chat_id, from_id, to_id)
        if key not in self._pending:
            return {"ok": False, "message": "没有待确认的求婚请求！"}

        del self._pending[key]
        return {"ok": True}

    def has_pending(self, chat_id: int, from_id: int, to_id: int) -> bool:
        """检查是否有待确认的求婚"""
        return (chat_id, from_id, to_id) in self._pending

    async def divorce(self, chat_id: int, user_id: int) -> dict:
        """离婚，退一半积分"""
        partner_id = await redis_db.get_marry(chat_id, user_id)
        if partner_id is None:
            return {"ok": False, "message": "你还没有结婚！"}

        # 计算退还积分
        refund = config.MARRY_COST // 2

        # 解除婚姻关系
        await redis_db.del_marry(chat_id, user_id)
        await redis_db.del_marry(chat_id, partner_id)

        # 退还一半积分
        await redis_db.add_points(chat_id, user_id, refund)

        # 更新SQLite
        await sqlite_db.deactivate_marriage(chat_id, user_id)

        return {"ok": True, "refund": refund, "partner_id": partner_id}

    async def get_partner(self, chat_id: int, user_id: int) -> int | None:
        """获取伴侣ID"""
        return await redis_db.get_marry(chat_id, user_id)

    async def get_couples_rank(self, chat_id: int) -> list[dict]:
        """获取情侣榜"""
        couples = await sqlite_db.get_couples(chat_id, limit=10)
        result = []
        for couple in couples:
            result.append({
                "user1_id": couple["user1_id"],
                "user2_id": couple["user2_id"],
                "created_at": couple["created_at"],
            })
        return result


marry_service = MarryService()