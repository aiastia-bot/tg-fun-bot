import random

from database.redis_db import redis_db
from database.sqlite_db import sqlite_db


class GameService:

    async def dice(self, chat_id: int, user_id: int, amount: int) -> dict:
        """掷骰子：大于3赢，赔率1:1"""
        # 检查下注限制
        limit_check = await self._check_bet_limit(chat_id, user_id, amount)
        if not limit_check["ok"]:
            return limit_check

        # 扣除积分
        await redis_db.add_points(chat_id, user_id, -amount)

        # 掷骰子
        result = random.randint(1, 6)

        # 获取卡片加成
        bonus = await self._get_game_bonus(chat_id, user_id, "dice")

        if result > 3:
            # 赢了
            winnings = int(amount * 2 * (1 + bonus))
            profit = winnings - amount
            await redis_db.add_points(chat_id, user_id, winnings)
            await sqlite_db.add_game_record(chat_id, user_id, "dice", amount, f"掷出{result}", profit)
            return {
                "ok": True,
                "win": True,
                "result": result,
                "winnings": winnings,
                "profit": profit,
                "bonus": bonus,
            }
        else:
            # 输了
            await sqlite_db.add_game_record(chat_id, user_id, "dice", amount, f"掷出{result}", -amount)
            return {
                "ok": True,
                "win": False,
                "result": result,
                "loss": amount,
                "bonus": bonus,
            }

    async def slot(self, chat_id: int, user_id: int, amount: int) -> dict:
        """老虎机：全同×10，两个同×2"""
        limit_check = await self._check_bet_limit(chat_id, user_id, amount)
        if not limit_check["ok"]:
            return limit_check

        await redis_db.add_points(chat_id, user_id, -amount)

        # 老虎机符号
        symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎", "7️⃣", "🎰"]
        reels = [random.choice(symbols) for _ in range(3)]

        bonus = await self._get_game_bonus(chat_id, user_id, "slot")

        if reels[0] == reels[1] == reels[2]:
            # 三个相同 ×10
            winnings = int(amount * 10 * (1 + bonus))
            profit = winnings - amount
            await redis_db.add_points(chat_id, user_id, winnings)
            await sqlite_db.add_game_record(chat_id, user_id, "slot", amount, f"{''.join(reels)}", profit)
            return {
                "ok": True,
                "win": True,
                "reels": reels,
                "multiplier": 10,
                "winnings": winnings,
                "profit": profit,
                "bonus": bonus,
                "jackpot": True,
            }
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            # 两个相同 ×2
            winnings = int(amount * 2 * (1 + bonus))
            profit = winnings - amount
            await redis_db.add_points(chat_id, user_id, winnings)
            await sqlite_db.add_game_record(chat_id, user_id, "slot", amount, f"{''.join(reels)}", profit)
            return {
                "ok": True,
                "win": True,
                "reels": reels,
                "multiplier": 2,
                "winnings": winnings,
                "profit": profit,
                "bonus": bonus,
                "jackpot": False,
            }
        else:
            # 没有相同
            await sqlite_db.add_game_record(chat_id, user_id, "slot", amount, f"{''.join(reels)}", -amount)
            return {
                "ok": True,
                "win": False,
                "reels": reels,
                "loss": amount,
                "bonus": bonus,
            }

    async def coin(self, chat_id: int, user_id: int, amount: int, choice: str) -> dict:
        """猜正反：赔率1:1"""
        limit_check = await self._check_bet_limit(chat_id, user_id, amount)
        if not limit_check["ok"]:
            return limit_check

        if choice not in ("正", "反", "heads", "tails"):
            return {"ok": False, "message": "请选择「正」或「反」"}

        await redis_db.add_points(chat_id, user_id, -amount)

        result = random.choice(["正", "反"])
        bonus = await self._get_game_bonus(chat_id, user_id, "coin")

        # 统一中文
        choice_cn = "正" if choice in ("正", "heads") else "反"
        won = choice_cn == result

        if won:
            winnings = int(amount * 2 * (1 + bonus))
            profit = winnings - amount
            await redis_db.add_points(chat_id, user_id, winnings)
            await sqlite_db.add_game_record(chat_id, user_id, "coin", amount, f"猜{choice_cn} 结果{result}", profit)
            return {
                "ok": True,
                "win": True,
                "result": result,
                "choice": choice_cn,
                "winnings": winnings,
                "profit": profit,
                "bonus": bonus,
            }
        else:
            await sqlite_db.add_game_record(chat_id, user_id, "coin", amount, f"猜{choice_cn} 结果{result}", -amount)
            return {
                "ok": True,
                "win": False,
                "result": result,
                "choice": choice_cn,
                "loss": amount,
                "bonus": bonus,
            }

    async def roulette(self, chat_id: int, user_id: int, amount: int, option: str) -> dict:
        """轮盘：红/黑/数字"""
        limit_check = await self._check_bet_limit(chat_id, user_id, amount)
        if not limit_check["ok"]:
            return limit_check

        # 红黑对应数字
        red_numbers = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        black_numbers = {2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35}

        if option not in ("红", "黑", "red", "black") and not option.isdigit():
            return {"ok": False, "message": "请选择「红」「黑」或数字(0-36)"}

        await redis_db.add_points(chat_id, user_id, -amount)

        result_num = random.randint(0, 36)
        result_color = "绿" if result_num == 0 else ("红" if result_num in red_numbers else "黑")
        bonus = await self._get_game_bonus(chat_id, user_id, "roulette")

        # 判断输赢
        win = False
        multiplier = 0

        if option in ("红", "red"):
            if result_num in red_numbers:
                win = True
                multiplier = 2
        elif option in ("黑", "black"):
            if result_num in black_numbers:
                win = True
                multiplier = 2
        elif option.isdigit():
            if int(option) == result_num:
                win = True
                multiplier = 36

        if win:
            winnings = int(amount * multiplier * (1 + bonus))
            profit = winnings - amount
            await redis_db.add_points(chat_id, user_id, winnings)
            await sqlite_db.add_game_record(chat_id, user_id, "roulette", amount, f"选{option} 结果{result_num}{result_color}", profit)
            return {
                "ok": True,
                "win": True,
                "result_num": result_num,
                "result_color": result_color,
                "option": option,
                "multiplier": multiplier,
                "winnings": winnings,
                "profit": profit,
                "bonus": bonus,
            }
        else:
            await sqlite_db.add_game_record(chat_id, user_id, "roulette", amount, f"选{option} 结果{result_num}{result_color}", -amount)
            return {
                "ok": True,
                "win": False,
                "result_num": result_num,
                "result_color": result_color,
                "option": option,
                "loss": amount,
                "bonus": bonus,
            }

    async def guess_number(self, chat_id: int, user_id: int, guess: int) -> dict:
        """猜数字(1-100)，每次消耗10积分"""
        amount = 10
        points = await redis_db.get_points(chat_id, user_id)
        if points < amount:
            return {"ok": False, "message": f"积分不足！猜数字需要 {amount} 积分，你只有 {points}"}

        await redis_db.add_points(chat_id, user_id, -amount)

        # 生成或获取当前游戏的数字
        target_key = f"guess:{chat_id}:{user_id}"
        target = await redis_db.client.get(target_key)
        attempts_key = f"guess_attempts:{chat_id}:{user_id}"

        if target is None:
            target = random.randint(1, 100)
            await redis_db.client.set(target_key, str(target))
            await redis_db.client.set(attempts_key, "0")

        target = int(target)
        attempts = int(await redis_db.client.get(attempts_key) or "0")
        attempts += 1
        await redis_db.client.set(attempts_key, str(attempts))

        if guess == target:
            # 猜对了，奖励积分
            reward = max(50, 200 - (attempts - 1) * 20)
            await redis_db.add_points(chat_id, user_id, reward)
            await redis_db.client.delete(target_key)
            await redis_db.client.delete(attempts_key)
            await sqlite_db.add_game_record(chat_id, user_id, "guess", amount * attempts, f"猜{attempts}次", reward)
            return {
                "ok": True,
                "win": True,
                "target": target,
                "attempts": attempts,
                "reward": reward,
                "total_cost": amount * attempts,
            }
        elif guess < target:
            await sqlite_db.add_game_record(chat_id, user_id, "guess", amount, f"第{attempts}次猜{guess}(小了)", -amount)
            return {
                "ok": True,
                "win": False,
                "hint": "小了 ⬆️",
                "attempts": attempts,
            }
        else:
            await sqlite_db.add_game_record(chat_id, user_id, "guess", amount, f"第{attempts}次猜{guess}(大了)", -amount)
            return {
                "ok": True,
                "win": False,
                "hint": "大了 ⬇️",
                "attempts": attempts,
            }

    async def _check_bet_limit(self, chat_id: int, user_id: int, amount: int) -> dict:
        """检查下注限制"""
        if amount <= 0:
            return {"ok": False, "message": "下注金额必须大于0！"}

        # 检查下注上限
        bet_limit = await redis_db.get_bet_limit(chat_id)
        if bet_limit > 0 and amount > bet_limit:
            return {"ok": False, "message": f"下注金额超过上限！当前上限：{bet_limit}"}

        # 检查余额
        points = await redis_db.get_points(chat_id, user_id)
        if points < amount:
            return {"ok": False, "message": f"积分不足！你有 {points}，下注 {amount}"}

        return {"ok": True}

    async def _get_game_bonus(self, chat_id: int, user_id: int, game_type: str) -> float:
        """获取卡片加成"""
        card = await sqlite_db.get_best_bonus_card(chat_id, user_id, f"game_{game_type}")
        if card:
            return card["bonus_value"]
        return 0.0

    async def gift_points(self, chat_id: int, from_id: int, to_id: int, amount: int) -> dict:
        """转赠积分"""
        if from_id == to_id:
            return {"ok": False, "message": "不能转给自己！"}

        if amount <= 0:
            return {"ok": False, "message": "金额必须大于0！"}

        points = await redis_db.get_points(chat_id, from_id)
        if points < amount:
            return {"ok": False, "message": f"积分不足！你有 {points}"}

        await redis_db.add_points(chat_id, from_id, -amount)
        await redis_db.add_points(chat_id, to_id, amount)

        return {"ok": True, "amount": amount}


game_service = GameService()