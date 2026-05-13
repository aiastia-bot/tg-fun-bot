from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from database.redis_db import redis_db
from database.sqlite_db import sqlite_db
from services.game_service import game_service

router = Router()

BET_AMOUNTS = [10, 50, 100, 500, 1000]


def _parse_amount(text: str) -> int | None:
    """解析金额参数"""
    parts = text.split()
    if len(parts) < 2:
        return None
    try:
        return int(parts[1])
    except (ValueError, IndexError):
        return None


def _bet_keyboard(game: str) -> InlineKeyboardMarkup:
    """下注金额选择按钮"""
    buttons = []
    row = []
    for amount in BET_AMOUNTS:
        row.append(InlineKeyboardButton(
            text=f"💎 {amount}",
            callback_data=f"bet:{game}:{amount}"
        ))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _choice_keyboard(game: str, amount: int) -> InlineKeyboardMarkup:
    """游戏选项按钮（正反/红黑）"""
    if game == "coin":
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="🟡 正面", callback_data=f"play:coin:{amount}:正"),
            InlineKeyboardButton(text="🔵 反面", callback_data=f"play:coin:{amount}:反"),
        ]])
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🔴 红", callback_data=f"play:roulette:{amount}:红"),
        InlineKeyboardButton(text="⚫ 黑", callback_data=f"play:roulette:{amount}:黑"),
    ]])


# ========== Text Formatters ==========

async def _dice_text(chat_id: int, user_id: int, result: dict) -> str:
    dice_emoji = "⚀⚁⚂⚃⚄⚅"
    dice_face = dice_emoji[result["result"] - 1]
    if result["win"]:
        text = "🎲 掷骰子\n\n"
        text += f"结果：{dice_face} ({result['result']})\n"
        text += "🎉 你赢了！\n"
        text += f"💰 赢得：+{result['profit']}"
        if result["bonus"] > 0:
            text += f"\n🃏 卡片加成：+{result['bonus']*100:.0f}%"
    else:
        text = "🎲 掷骰子\n\n"
        text += f"结果：{dice_face} ({result['result']})\n"
        text += "😢 你输了…\n"
        text += f"💸 失去：-{result['loss']}"
    points = await redis_db.get_points(chat_id, user_id)
    text += f"\n💎 当前积分：{points}"
    return text


async def _slot_text(chat_id: int, user_id: int, result: dict) -> str:
    reels_str = " | ".join(result["reels"])
    if result["win"]:
        text = "🎰 老虎机\n\n"
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
        text = "🎰 老虎机\n\n"
        text += f"{reels_str}\n\n"
        text += "😢 没有匹配…\n"
        text += f"💸 失去：-{result['loss']}"
    points = await redis_db.get_points(chat_id, user_id)
    text += f"\n💎 当前积分：{points}"
    return text


async def _coin_text(chat_id: int, user_id: int, result: dict) -> str:
    coin_emoji = "🟡" if result["result"] == "正" else "🔵"
    if result["win"]:
        text = "🪙 猜正反\n\n"
        text += f"你的选择：{result['choice']}\n"
        text += f"结果：{coin_emoji} {result['result']}\n"
        text += "🎉 猜对了！\n"
        text += f"💰 赢得：+{result['profit']}"
        if result["bonus"] > 0:
            text += f"\n🃏 卡片加成：+{result['bonus']*100:.0f}%"
    else:
        text = "🪙 猜正反\n\n"
        text += f"你的选择：{result['choice']}\n"
        text += f"结果：{coin_emoji} {result['result']}\n"
        text += "😢 猜错了…\n"
        text += f"💸 失去：-{result['loss']}"
    points = await redis_db.get_points(chat_id, user_id)
    text += f"\n💎 当前积分：{points}"
    return text


async def _roulette_text(chat_id: int, user_id: int, result: dict) -> str:
    color_emoji = {"红": "🔴", "黑": "⚫", "绿": "🟢"}
    emoji = color_emoji.get(result["result_color"], "⚪")
    if result["win"]:
        text = "🎡 轮盘\n\n"
        text += f"你的选择：{result['option']}\n"
        text += f"结果：{emoji} {result['result_num']} ({result['result_color']})\n"
        text += "🎉 中了！\n"
        text += f"倍率：×{result['multiplier']}\n"
        text += f"💰 赢得：+{result['profit']}"
        if result["bonus"] > 0:
            text += f"\n🃏 卡片加成：+{result['bonus']*100:.0f}%"
    else:
        text = "🎡 轮盘\n\n"
        text += f"你的选择：{result['option']}\n"
        text += f"结果：{emoji} {result['result_num']} ({result['result_color']})\n"
        text += "😢 没中…\n"
        text += f"💸 失去：-{result['loss']}"
    points = await redis_db.get_points(chat_id, user_id)
    text += f"\n💎 当前积分：{points}"
    return text


# ========== Command Handlers ==========

@router.message(Command("dice"))
async def cmd_dice(message: types.Message):
    """掷骰子"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    await sqlite_db.ensure_user(user_id, message.from_user.username or "", message.from_user.first_name or "")

    amount = _parse_amount(message.text or "")
    if amount is None:
        await message.reply("🎲 掷骰子\n\n选择下注金额：", reply_markup=_bet_keyboard("dice"))
        return

    result = await game_service.dice(chat_id, user_id, amount)
    if not result["ok"]:
        await message.reply(f"❌ {result['message']}")
        return

    await message.reply(await _dice_text(chat_id, user_id, result))


@router.message(Command("slot"))
async def cmd_slot(message: types.Message):
    """老虎机"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    await sqlite_db.ensure_user(user_id, message.from_user.username or "", message.from_user.first_name or "")

    amount = _parse_amount(message.text or "")
    if amount is None:
        await message.reply("🎰 老虎机\n\n选择下注金额：", reply_markup=_bet_keyboard("slot"))
        return

    result = await game_service.slot(chat_id, user_id, amount)
    if not result["ok"]:
        await message.reply(f"❌ {result['message']}")
        return

    await message.reply(await _slot_text(chat_id, user_id, result))


@router.message(Command("coin"))
async def cmd_coin(message: types.Message):
    """猜正反"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    await sqlite_db.ensure_user(user_id, message.from_user.username or "", message.from_user.first_name or "")

    parts = (message.text or "").split()
    if len(parts) >= 3:
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
        await message.reply(await _coin_text(chat_id, user_id, result))
        return

    # 无参数时显示按钮
    await message.reply("🪙 猜正反\n\n选择下注金额：", reply_markup=_bet_keyboard("coin"))


@router.message(Command("roulette"))
async def cmd_roulette(message: types.Message):
    """轮盘"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    await sqlite_db.ensure_user(user_id, message.from_user.username or "", message.from_user.first_name or "")

    parts = (message.text or "").split()
    if len(parts) >= 3:
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
        await message.reply(await _roulette_text(chat_id, user_id, result))
        return

    # 无参数时显示按钮
    await message.reply("🎡 轮盘\n\n选择下注金额：", reply_markup=_bet_keyboard("roulette"))


@router.message(Command("guess"))
async def cmd_guess(message: types.Message):
    """猜数字"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    await sqlite_db.ensure_user(user_id, message.from_user.username or "", message.from_user.first_name or "")

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.reply("用法：/guess ＜1-100的数字＞\n示例：/guess 50\n每次消耗10积分")
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
        text = "🎯 猜数字 - 猜对了！\n\n"
        text += f"答案：{result['target']}\n"
        text += f"尝试次数：{result['attempts']} 次\n"
        text += f"消耗积分：{result['total_cost']}\n"
        text += f"🎉 奖励：+{result['reward']}"
    else:
        text = f"🎯 猜数字 - 第 {result['attempts']} 次\n\n"
        text += f"你猜的：{guess}\n"
        text += f"提示：{result['hint']}\n"
        text += "消耗：10 积分\n"
        text += "继续猜：/guess ＜数字＞"

    points = await redis_db.get_points(chat_id, user_id)
    text += f"\n💎 当前积分：{points}"

    await message.reply(text)


@router.message(Command("gift"))
async def cmd_gift(message: types.Message):
    """转赠积分"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    await sqlite_db.ensure_user(user_id, message.from_user.username or "", message.from_user.first_name or "")

    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.reply("用法：/gift ＜金额＞ @用户\n示例：/gift 100 @friend")
        return

    try:
        amount = int(parts[1])
    except ValueError:
        await message.reply("金额必须是数字！")
        return

    if not message.reply_to_message:
        await message.reply("请回复要转赠的人的消息，或使用 /gift ＜金额＞ 回复某人的消息")
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


# ========== Callback Handlers ==========

@router.callback_query(lambda c: c.data and c.data.startswith("bet:"))
async def callback_bet(callback: CallbackQuery):
    """处理下注金额按钮"""
    _, game, amount_str = callback.data.split(":")
    amount = int(amount_str)
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    await sqlite_db.ensure_user(user_id, callback.from_user.username or "", callback.from_user.first_name or "")

    if game in ("coin", "roulette"):
        game_name = {"coin": "🪙 猜正反", "roulette": "🎡 轮盘"}[game]
        await callback.message.edit_text(
            f"{game_name}\n下注：{amount} 💎\n\n请选择：",
            reply_markup=_choice_keyboard(game, amount)
        )
    elif game == "dice":
        result = await game_service.dice(chat_id, user_id, amount)
        if not result["ok"]:
            await callback.message.edit_text(f"❌ {result['message']}")
        else:
            await callback.message.edit_text(await _dice_text(chat_id, user_id, result))
    elif game == "slot":
        result = await game_service.slot(chat_id, user_id, amount)
        if not result["ok"]:
            await callback.message.edit_text(f"❌ {result['message']}")
        else:
            await callback.message.edit_text(await _slot_text(chat_id, user_id, result))

    await callback.answer()


@router.callback_query(lambda c: c.data and c.data.startswith("play:"))
async def callback_play(callback: CallbackQuery):
    """处理游戏选项按钮（正反/红黑）"""
    _, game, amount_str, choice = callback.data.split(":")
    amount = int(amount_str)
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    await sqlite_db.ensure_user(user_id, callback.from_user.username or "", callback.from_user.first_name or "")

    if game == "coin":
        result = await game_service.coin(chat_id, user_id, amount, choice)
        if not result["ok"]:
            await callback.message.edit_text(f"❌ {result['message']}")
        else:
            await callback.message.edit_text(await _coin_text(chat_id, user_id, result))
    elif game == "roulette":
        result = await game_service.roulette(chat_id, user_id, amount, choice)
        if not result["ok"]:
            await callback.message.edit_text(f"❌ {result['message']}")
        else:
            await callback.message.edit_text(await _roulette_text(chat_id, user_id, result))

    await callback.answer()