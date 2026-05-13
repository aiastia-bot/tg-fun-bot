import redis.asyncio as redis
from config import config


class RedisDB:
    def __init__(self):
        self.client: redis.Redis | None = None

    async def connect(self):
        self.client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD or None,
            db=config.REDIS_DB,
            decode_responses=True,
        )

    async def close(self):
        if self.client:
            await self.client.close()

    # ========== 积分 ==========

    async def get_points(self, chat_id: int, user_id: int) -> int:
        """获取用户积分"""
        key = f"points:{chat_id}:{user_id}"
        val = await self.client.get(key)
        return int(val) if val else 0

    async def set_points(self, chat_id: int, user_id: int, points: int):
        """设置用户积分"""
        key = f"points:{chat_id}:{user_id}"
        if points < 0:
            points = 0
        await self.client.set(key, str(points))
        # 更新排行榜
        await self.client.zadd(f"rank:{chat_id}", {str(user_id): points})

    async def add_points(self, chat_id: int, user_id: int, amount: int) -> int:
        """增加/减少积分，返回最新积分"""
        current = await self.get_points(chat_id, user_id)
        new_points = max(0, current + amount)
        await self.set_points(chat_id, user_id, new_points)
        return new_points

    # ========== 签到 ==========

    async def get_sign_date(self, chat_id: int, user_id: int) -> str:
        """获取上次签到日期"""
        key = f"sign:{chat_id}:{user_id}"
        return await self.client.get(key) or ""

    async def set_sign_date(self, chat_id: int, user_id: int, date_str: str):
        """设置签到日期"""
        key = f"sign:{chat_id}:{user_id}"
        await self.client.set(key, date_str)

    async def get_streak(self, chat_id: int, user_id: int) -> int:
        """获取连续签到天数"""
        key = f"streak:{chat_id}:{user_id}"
        val = await self.client.get(key)
        return int(val) if val else 0

    async def set_streak(self, chat_id: int, user_id: int, days: int):
        """设置连续签到天数"""
        key = f"streak:{chat_id}:{user_id}"
        await self.client.set(key, str(days))

    # ========== 排行榜 ==========

    async def get_rank(self, chat_id: int, top_n: int = 10) -> list[tuple[str, float]]:
        """获取排行榜前N名"""
        key = f"rank:{chat_id}"
        return await self.client.zrevrangebyscore(key, "+inf", "-inf", withscores=True, start=0, num=top_n)

    async def get_user_rank(self, chat_id: int, user_id: int) -> int:
        """获取用户排名（从0开始）"""
        key = f"rank:{chat_id}"
        rank = await self.client.zrevrank(key, str(user_id))
        return rank if rank is not None else -1

    # ========== 结婚 ==========

    async def get_marry(self, chat_id: int, user_id: int) -> int | None:
        """获取结婚对象"""
        key = f"marry:{chat_id}:{user_id}"
        val = await self.client.get(key)
        return int(val) if val else None

    async def set_marry(self, chat_id: int, user_id: int, target_id: int):
        """设置结婚对象"""
        key = f"marry:{chat_id}:{user_id}"
        await self.client.set(key, str(target_id))

    async def del_marry(self, chat_id: int, user_id: int):
        """删除结婚记录"""
        key = f"marry:{chat_id}:{user_id}"
        await self.client.delete(key)

    # ========== 下注上限 ==========

    async def get_bet_limit(self, chat_id: int) -> int:
        """获取群组下注上限"""
        key = f"bet_limit:{chat_id}"
        val = await self.client.get(key)
        return int(val) if val else config.DEFAULT_BET_LIMIT

    async def set_bet_limit(self, chat_id: int, limit: int):
        """设置群组下注上限"""
        key = f"bet_limit:{chat_id}"
        await self.client.set(key, str(limit))

    # ========== 群组列表 ==========

    async def add_chat(self, chat_id: int, chat_title: str):
        """记录Bot加入的群组"""
        key = "bot_chats"
        await self.client.hset(key, str(chat_id), chat_title)

    async def remove_chat(self, chat_id: int):
        """记录Bot离开的群组"""
        key = "bot_chats"
        await self.client.hdel(key, str(chat_id))

    async def get_all_chats(self) -> dict[str, str]:
        """获取所有群组"""
        key = "bot_chats"
        return await self.client.hgetall(key)

    # ========== 提醒 ==========

    async def add_reminder(self, user_id: int, remind_id: str, data: str):
        """添加提醒"""
        key = f"reminders:{user_id}"
        await self.client.hset(key, remind_id, data)

    async def get_reminders(self, user_id: int) -> dict[str, str]:
        """获取用户所有提醒"""
        key = f"reminders:{user_id}"
        return await self.client.hgetall(key)

    async def del_reminder(self, user_id: int, remind_id: str):
        """删除提醒"""
        key = f"reminders:{user_id}"
        await self.client.hdel(key, remind_id)


redis_db = RedisDB()