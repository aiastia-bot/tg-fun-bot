import random
from datetime import date, timedelta

from config import config
from database.redis_db import redis_db
from database.sqlite_db import sqlite_db


class SignService:

    async def daily_sign(self, chat_id: int, user_id: int) -> dict:
        """普通签到"""
        today = date.today().isoformat()
        last_sign = await redis_db.get_sign_date(chat_id, user_id)

        # 检查是否已签到
        if last_sign == today:
            streak = await redis_db.get_streak(chat_id, user_id)
            points = await redis_db.get_points(chat_id, user_id)
            return {
                "success": False,
                "message": "今天已经签到了哦～明天再来吧！",
                "streak": streak,
                "points": points,
            }

        # 计算连续签到
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        current_streak = await redis_db.get_streak(chat_id, user_id)

        if last_sign == yesterday:
            new_streak = current_streak + 1
        else:
            new_streak = 1

        # 计算积分
        base_points = config.SIGN_BASE_POINTS
        multiplier = self._get_streak_multiplier(new_streak)

        # 检查是否已婚（额外加成）
        marry_bonus = 1.0
        marry_target = await redis_db.get_marry(chat_id, user_id)
        if marry_target is not None:
            marry_bonus = config.MARRY_SIGN_BONUS

        earned = int(base_points * multiplier * marry_bonus)

        # 更新数据
        await redis_db.set_sign_date(chat_id, user_id, today)
        await redis_db.set_streak(chat_id, user_id, new_streak)
        new_points = await redis_db.add_points(chat_id, user_id, earned)

        return {
            "success": True,
            "earned": earned,
            "base_points": base_points,
            "multiplier": multiplier,
            "marry_bonus": marry_bonus,
            "streak": new_streak,
            "points": new_points,
        }

    async def gamble_sign(self, chat_id: int, user_id: int) -> dict:
        """赌博签到：随机积分"""
        today = date.today().isoformat()
        last_sign = await redis_db.get_sign_date(chat_id, user_id)

        # 检查是否已签到
        if last_sign == today:
            streak = await redis_db.get_streak(chat_id, user_id)
            points = await redis_db.get_points(chat_id, user_id)
            return {
                "success": False,
                "message": "今天已经签到了哦～明天再来吧！",
                "streak": streak,
                "points": points,
            }

        # 计算连续签到
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        current_streak = await redis_db.get_streak(chat_id, user_id)

        if last_sign == yesterday:
            new_streak = current_streak + 1
        else:
            new_streak = 1

        # 随机积分
        min_val = config.GAMBLE_SIGN_MIN
        max_val = config.GAMBLE_SIGN_MAX
        earned = random.randint(min_val, max_val)

        # 更新数据
        await redis_db.set_sign_date(chat_id, user_id, today)
        await redis_db.set_streak(chat_id, user_id, new_streak)
        new_points = await redis_db.add_points(chat_id, user_id, earned)

        return {
            "success": True,
            "earned": earned,
            "gamble_range": (min_val, max_val),
            "streak": new_streak,
            "points": new_points,
            "is_lucky": earned > 0,
        }

    def _get_streak_multiplier(self, streak: int) -> float:
        """根据连续签到天数获取加成倍率"""
        multiplier = 1.0
        for days, bonus in sorted(config.STREAK_BONUS.items(), reverse=True):
            if streak >= days:
                multiplier = bonus
                break
        return multiplier

    async def get_user_info(self, chat_id: int, user_id: int) -> dict:
        """获取用户签到信息"""
        points = await redis_db.get_points(chat_id, user_id)
        streak = await redis_db.get_streak(chat_id, user_id)
        rank = await redis_db.get_user_rank(chat_id, user_id)
        last_sign = await redis_db.get_sign_date(chat_id, user_id)
        marry_target = await redis_db.get_marry(chat_id, user_id)
        multiplier = self._get_streak_multiplier(streak)

        return {
            "points": points,
            "streak": streak,
            "rank": rank + 1 if rank >= 0 else -1,
            "last_sign": last_sign,
            "multiplier": multiplier,
            "next_bonus": self._get_next_bonus(streak),
            "is_married": marry_target is not None,
        }

    def _get_next_bonus(self, streak: int) -> dict | None:
        """获取下一个加成目标"""
        for days, bonus in sorted(config.STREAK_BONUS.items()):
            if streak < days:
                return {"days": days, "multiplier": bonus}
        return None


sign_service = SignService()