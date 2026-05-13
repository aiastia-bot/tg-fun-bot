from aiogram import Router, types
from aiogram.filters import Command

from database.redis_db import redis_db
from database.sqlite_db import sqlite_db
from services.game_service import game_service

router = Router()


def _parse_amount(text: str) -> int | None:
    """解析金额参数"""
    parts = text.split()
    if len(parts) < 2:
        return None
    try:
        amount = int(parts[1])
        return amount
    except (ValueError, IndexError):
        return None


@router.message(Command("dice"))
async def cmd_dice(message: types.Message):
    """掷骰子"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )

    amount = _parse_amount(message.text or "")
    if amount is None:
        await message.reply("用法：/dice <金额>\n示例：/dice 100")
        return

    result = await game_service.dice(chat_id, user_id, amount)

    if not result["ok"]:
        await message.reply(f"❌ {result['message']}")
        return

    dice_emoji = "⚀⚁⚂⚃⚄⚅"
    dice_face = dice_emoji[result["result"] - 1]

    if result["win"]:
        text = f"🎲 掷骰子\n\n"
        text += f"结果：{dice_face} ({result['result']})\n"
        text += f"🎉 你赢了！\n"
        text += f"💰 赢得：+{result['profit']}"
        if result["bonus"] > 0:
            text += f"\n🃏 卡片加成：+{result['bonus']*100:.0f}%"
    else:
        text = f"🎲 掷骰子\n\n"
        text += f"结果：{dice_face} ({result['result']})\n"
        text += f"😢 你输了…\n"
        text += f"💸 失去：-{result['loss']}"

    points = await redis_db.get_points(chat_id, user_id)
    text += f"\n💎 当前积分：{points}"

    await message.reply(text)


@router.message(Command("slot"))
async def cmd_slot(message: types.Message):
    """老虎机"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )

    amount = _parse_amount(message.text or "")
    if amount is None:
        await message.reply("用法：/slot <金额>\n示例：/slot 100")
        return

    result = await game_service.slot(chat_id, user_id, amount)

    if not result["ok"]:
        await message.reply(f"❌ {result['message']}")
        return

    reels_str = " | ".join(result["reels"])

    if result["win"]:
        text = f"🎰 老虎机\n\n"
        text += f"{reels_str}\n\n"
        if result["jackpot"]:
            text += "🎊 大满贯！三个相同！\n"
        else:
            text += "🎉 两个相同！\n"
        text += f"倍率：×{result['multiplier']}\n"
        text += f"💰 赢得：+{result['profit']}"
        if result["bonus"] > 0:
            text += f"\n🃏 卡片加成：+{result['bonus']*100:.0f}%"
    else:
        text = f"🎰 老虎机\n\n"
        text += f"{reels_str}\n\n"
        text += f"😢 没有匹配…\n"
        text += f"💸 失去：-{result['loss']}"

    points = await redis_db.get_points(chat_id, user_id)
    text += f"\n💎 当前积分：{points}"

    await message.reply(text)


@router.message(Command("coin"))
async def cmd_coin(message: types.Message):
    """猜正反"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )

    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.reply("用法：/coin <金额> <正/反>\n示例：/coin 100 正")
        return

    try:
        amount = int(parts[1])
    except ValueError:
        await message.reply("金额必须是数字！")
        return

    choice = parts[2]
    result = await game_service.coin(chat_id, user_id, amount, choice)

    if not result["ok"]:
        await message.reply(f"❌ {result['message']}")
        return

    coin_emoji = "🟡" if result["result"] == "正" else "🔵"

    if result["win"]:
        text = f"🪙 猜正反\n\n"
        text += f"你的选择：{result['choice']}\n"
        text += f"结果：{coin_emoji} {result['result']}\n"
        text += f"🎉 猜对了！\n"
        text += f"💰 赢得：+{result['profit']}"
        if result["bonus"] > 0:
            text += f"\n🃏 卡片加成：+{result['bonus']*100:.0f}%"
    else:
        text = f"🪙 猜正反\n\n"
        text += f"你的选择：{result['choice']}\n"
        text += f"结果：{coin_emoji} {result['result']}\n"
        text += f"😢 猜错了…\n"
        text += f"💸 失去：-{result['loss']}"

    points = await redis_db.get_points(chat_id, user_id)
    text += f"\n💎 当前积分：{points}"

    await message.reply(text)


@router.message(Command("roulette"))
async def cmd_roulette(message: types.Message):
    """轮盘"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )

    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.reply("用法：/roulette <金额> <红/黑/数字>\n示例：/roulette 100 红")
        return

    try:
        amount = int(parts[1])
    except ValueError:
        await message.reply("金额必须是数字！")
        return

    option = parts[2]
    result = await game_service.roulette(chat_id, user_id, amount, option)

    if not result["ok"]:
        await message.reply(f"❌ {result['message']}")
        return

    color_emoji = {"红": "🔴", "黑": "⚫", "绿": "🟢"}
    emoji = color_emoji.get(result["result_color"], "⚪")

    if result["win"]:
        text = f"🎡 轮盘\n\n"
        text += f"你的选择：{result['option']}\n"
        text += f"结果：{emoji} {result['result_num']} ({result['result_color']})\n"
        text += f"🎉 中了！\n"
        text += f"倍率：×{result['multiplier']}\n"
        text += f"💰 赢得：+{result['profit']}"
        if result["bonus"] > 0:
            text += f"\n🃏 卡片加成：+{result['bonus']*100:.0f}%"
    else:
        text = f"🎡 轮盘\n\n"
        text += f"你的选择：{result['option']}\n"
        text += f"结果：{emoji} {result['result_num']} ({result['result_color']})\n"
        text += f"😢 没中…\n"
        text += f"💸 失去：-{result['loss']}"

    points = await redis_db.get_points(chat_id, user_id)
    text += f"\n💎 当前积分：{points}"

    await message.reply(text)


@router.message(Command("guess"))
async def cmd_guess(message: types.Message):
    """猜数字"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.reply("用法：/guess <1-100的数字>\n示例：/guess 50\n每次消耗10积分")
        return

    try:
        guess = int(parts[1])
    except ValueError:
        await message.reply("请输入1-100的数字！")
        return

    if guess < 1 or guess > 100:
        await message.reply("数字必须在1-100之间！")
        return

    result = await game_service.guess_number(chat_id, user_id, guess)

    if not result["ok"]:
        await message.reply(f"❌ {result['message']}")
        return

    if result["win"]:
        text = f"🎯 猜数字 - 猜对了！\n\n"
        text += f"答案：{result['target']}\n"
        text += f"尝试次数：{result['attempts']} 次\n"
        text += f"消耗积分：{result['total_cost']}\n"
        text += f"🎉 奖励：+{result['reward']}"
    else:
        text = f"🎯 猜数字 - 第 {result['attempts']} 次\n\n"
        text += f"你猜的：{guess}\n"
        text += f"提示：{result['hint']}\n"
        text += f"消耗：10 积分\n"
        text += "继续猜：/guess <数字>"

    points = await redis_db.get_points(chat_id, user_id)
    text += f"\n💎 当前积分：{points}"

    await message.reply(text)


@router.message(Command("gift"))
async def cmd_gift(message: types.Message):
    """转赠积分"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )

    # 解析：/gift <金额> @用户
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.reply("用法：/gift <金额> @用户\n示例：/gift 100 @friend")
        return

    try:
        amount = int(parts[1])
    except ValueError:
        await message.reply("金额必须是数字！")
        return

    # 获取目标用户
    if not message.reply_to_message:
        # 尝试从文本解析
        await message.reply("请回复要转赠的人的消息，或使用 /gift <金额> 回复某人的消息")
        return

    to_id = message.reply_to_message.from_user.id
    to_name = message.reply_to_message.from_user.first_name

    result = await game_service.gift_points(chat_id, user_id, to_id, amount)

    if not result["ok"]:
        await message.reply(f"❌ {result['message']}")
        return

    points = await redis_db.get_points(chat_id, user_id)
    await message.reply(
        f"🎁 转赠成功！\n\n"
        f"转赠给：{to_name}\n"
        f"金额：{result['amount']} 💎\n"
        f"你的剩余积分：{points}"
    )