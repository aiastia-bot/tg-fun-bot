import random

from config import config
from database.redis_db import redis_db
from database.sqlite_db import sqlite_db


# 卡池定义
CARD_POOL = {
    "角色": {
        "N": [
            ("小兵", "通用加成", 0.02),
            ("村民", "签到加成", 0.05),
            ("学徒", "通用加成", 0.03),
        ],
        "R": [
            ("骑士", "通用加成", 0.05),
            ("法师", "骰子加成", 0.08),
            ("猎人", "老虎机加成", 0.08),
        ],
        "SR": [
            ("龙骑士", "通用加成", 0.10),
            ("大魔导师", "骰子加成", 0.15),
            ("暗影刺客", "老虎机加成", 0.15),
        ],
        "SSR": [
            ("圣龙王", "通用加成", 0.20),
            ("命运女神", "轮盘加成", 0.25),
            ("幸运之星", "签到加成", 0.30),
        ],
    },
    "装备": {
        "N": [
            ("木剑", "通用加成", 0.02),
            ("布甲", "签到加成", 0.03),
        ],
        "R": [
            ("铁剑", "通用加成", 0.05),
            ("银盾", "硬币加成", 0.08),
        ],
        "SR": [
            ("魔法杖", "骰子加成", 0.12),
            ("黄金甲", "签到加成", 0.15),
        ],
        "SSR": [
            ("神器·天命", "通用加成", 0.20),
            ("神器·财运", "老虎机加成", 0.25),
        ],
    },
    "表情包": {
        "N": [
            ("😊 微笑", "无", 0),
            ("😂 大笑", "无", 0),
            ("🤔 思考", "无", 0),
        ],
        "R": [
            ("😎 酷", "无", 0),
            ("🥳 派对", "无", 0),
        ],
        "SR": [
            ("🦄 独角兽", "签到加成", 0.05),
            ("🌈 彩虹", "通用加成", 0.05),
        ],
        "SSR": [
            ("👑 皇冠", "通用加成", 0.10),
            ("💫 闪耀", "所有赌博加成", 0.15),
        ],
    },
}

# 稀有度概率（N=60%, R=25%, SR=12%, SSR=3%）
RARITY_WEIGHTS = {
    "N": 60,
    "R": 25,
    "SR": 12,
    "SSR": 3,
}

RARITY_EMOJI = {
    "N": "⚪",
    "R": "🔵",
    "SR": "🟣",
    "SSR": "🟡",
}


class DrawService:

    async def draw(self, chat_id: int, user_id: int) -> dict:
        """抽卡"""
        cost = config.DRAW_COST
        points = await redis_db.get_points(chat_id, user_id)

        if points < cost:
            return {"ok": False, "message": f"积分不足！抽卡需要 {cost} 积分，你只有 {points}"}

        # 扣除积分
        await redis_db.add_points(chat_id, user_id, -cost)

        # 随机稀有度
        rarities = list(RARITY_WEIGHTS.keys())
        weights = list(RARITY_WEIGHTS.values())
        rarity = random.choices(rarities, weights=weights, k=1)[0]

        # 随机类型
        card_types = list(CARD_POOL.keys())
        card_type = random.choice(card_types)

        # 随机卡片
        cards = CARD_POOL[card_type][rarity]
        card_name, bonus_type, bonus_value = random.choice(cards)

        # 存入数据库
        card_id = await sqlite_db.add_card(
            chat_id, user_id,
            card_name, rarity, card_type,
            bonus_type, bonus_value,
        )

        new_points = await redis_db.get_points(chat_id, user_id)

        return {
            "ok": True,
            "card_id": card_id,
            "card_name": card_name,
            "card_rarity": rarity,
            "card_type": card_type,
            "bonus_type": bonus_type,
            "bonus_value": bonus_value,
            "rarity_emoji": RARITY_EMOJI[rarity],
            "cost": cost,
            "points": new_points,
        }

    async def draw_ten(self, chat_id: int, user_id: int) -> dict:
        """十连抽"""
        cost = config.DRAW_COST * 10
        points = await redis_db.get_points(chat_id, user_id)

        if points < cost:
            return {"ok": False, "message": f"积分不足！十连抽需要 {cost} 积分，你只有 {points}"}

        # 扣除积分
        await redis_db.add_points(chat_id, user_id, -cost)

        cards = []
        for _ in range(10):
            # 随机稀有度（十连保底至少一个R）
            rarities = list(RARITY_WEIGHTS.keys())
            weights = list(RARITY_WEIGHTS.values())
            rarity = random.choices(rarities, weights=weights, k=1)[0]

            card_types = list(CARD_POOL.keys())
            card_type = random.choice(card_types)

            cards_pool = CARD_POOL[card_type][rarity]
            card_name, bonus_type, bonus_value = random.choice(cards_pool)

            card_id = await sqlite_db.add_card(
                chat_id, user_id,
                card_name, rarity, card_type,
                bonus_type, bonus_value,
            )

            cards.append({
                "card_id": card_id,
                "card_name": card_name,
                "card_rarity": rarity,
                "card_type": card_type,
                "bonus_type": bonus_type,
                "bonus_value": bonus_value,
                "rarity_emoji": RARITY_EMOJI[rarity],
            })

        # 保底：如果没有R以上，把第一个换成R
        if not any(c["card_rarity"] in ("R", "SR", "SSR") for c in cards):
            card_type = random.choice(list(CARD_POOL.keys()))
            cards_pool = CARD_POOL[card_type]["R"]
            card_name, bonus_type, bonus_value = random.choice(cards_pool)
            cards[0] = {
                "card_id": cards[0]["card_id"],
                "card_name": card_name,
                "card_rarity": "R",
                "card_type": card_type,
                "bonus_type": bonus_type,
                "bonus_value": bonus_value,
                "rarity_emoji": RARITY_EMOJI["R"],
            }

        new_points = await redis_db.get_points(chat_id, user_id)

        return {
            "ok": True,
            "cards": cards,
            "cost": cost,
            "points": new_points,
        }

    async def get_my_cards(self, chat_id: int, user_id: int) -> list[dict]:
        """获取我的卡片"""
        cards = await sqlite_db.get_user_cards(chat_id, user_id)
        for card in cards:
            card["rarity_emoji"] = RARITY_EMOJI.get(card["card_rarity"], "⚪")
        return cards

    def get_card_summary(self, cards: list[dict]) -> dict:
        """统计卡片"""
        summary = {"N": 0, "R": 0, "SR": 0, "SSR": 0}
        for card in cards:
            rarity = card.get("card_rarity", "N")
            if rarity in summary:
                summary[rarity] += 1
        return summary


draw_service = DrawService()