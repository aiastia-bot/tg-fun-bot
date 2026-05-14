import asyncio
import logging

from aiogram import Router, types
from aiogram.filters import Command

from database.redis_db import redis_db
from database.sqlite_db import sqlite_db
from services.sign_service import sign_service

router = Router()
logger = logging.getLogger(__name__)


async def _auto_delete(message: types.Message, reply: types.Message, delay: int = 60):
    """延迟删除用户消息和Bot回复，无权限时静默失败"""
    await asyncio.sleep(delay)
    try:
        await reply.delete()
    except Exception:
        pass
    try:
        await message.delete()
    except Exception:
        pass


@router.message(Command("sign"))
async def cmd_sign(message: types.Message):
    """每日签到"""
    if message.chat.type == "private":
        await message.reply("⚠️ 签到功能仅限群组使用！")
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # 确保用户存在
    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )
    # 记录群组
    if message.chat.type != "private":
        await redis_db.add_chat(chat_id, message.chat.title or "Unknown")

    result = await sign_service.daily_sign(chat_id, user_id)

    if not result["success"]:
        reply = await message.reply(
            f"⚠️ {result['message']}\n"
            f"📊 当前积分：{result['points']}\n"
            f"🔥 连续签到：{result['streak']} 天"
        )
        asyncio.create_task(_auto_delete(message, reply))
        return

    # 构建签到消息
    text = "✅ 签到成功！\n\n"
    text += f"💰 获得积分：+{result['earned']}\n"
    text += f"  ├ 基础积分：{result['base_points']}\n"
    text += f"  ├ 连续签到加成：×{result['multiplier']}\n"

    if result["marry_bonus"] > 1.0:
        text += f"  ├ 💍 婚姻加成：×{result['marry_bonus']}\n"

    text += f"🔥 连续签到：{result['streak']} 天\n"
    text += f"💎 当前积分：{result['points']}"

    reply = await message.reply(text)
    asyncio.create_task(_auto_delete(message, reply))


@router.message(Command("gsign"))
async def cmd_gamble_sign(message: types.Message):
    """赌博签到：随机积分"""
    if message.chat.type == "private":
        await message.reply("⚠️ 签到功能仅限群组使用！")
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )
    if message.chat.type != "private":
        await redis_db.add_chat(chat_id, message.chat.title or "Unknown")

    result = await sign_service.gamble_sign(chat_id, user_id)

    if not result["success"]:
        reply = await message.reply(
            f"⚠️ {result['message']}\n"
            f"📊 当前积分：{result['points']}\n"
            f"🔥 连续签到：{result['streak']} 天"
        )
        asyncio.create_task(_auto_delete(message, reply))
        return

    min_val, max_val = result["gamble_range"]

    if result["is_lucky"]:
        text = "🎰 赌博签到 - 运气不错！\n\n"
        text += f"💰 获得积分：+{result['earned']}\n"
    else:
        if result["earned"] < 0:
            text = "🎰 赌博签到 - 运气不佳…\n\n"
            text += f"💸 失去积分：{result['earned']}\n"
        else:
            text = "🎰 赌博签到 - 不好不坏\n\n"
            text += f"💰 获得积分：+{result['earned']}\n"

    text += f"🎲 随机范围：{min_val} ~ {max_val}\n"
    text += f"🔥 连续签到：{result['streak']} 天\n"
    text += f"💎 当前积分：{result['points']}"

    reply = await message.reply(text)
    asyncio.create_task(_auto_delete(message, reply))


@router.message(Command("me"))
async def cmd_me(message: types.Message):
    """查看个人信息"""
    if message.chat.type == "private":
        await message.reply("⚠️ 此功能仅限群组使用！")
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )

    info = await sign_service.get_user_info(chat_id, user_id)
    stats = await sqlite_db.get_game_stats(chat_id, user_id)

    text = f"👤 {message.from_user.first_name}"
    if message.from_user.username:
        text += f" (@{message.from_user.username})"
    text += "\n\n"
    text += f"💎 积分：{info['points']}\n"
    text += f"📊 排名：第 {info['rank']} 名\n"
    text += f"🔥 连续签到：{info['streak']} 天\n"
    text += f"⭐ 签到倍率：×{info['multiplier']}\n"

    if info["next_bonus"]:
        nb = info["next_bonus"]
        text += f"🎯 下一加成：{nb['days']}天 → ×{nb['multiplier']}\n"

    if info["is_married"]:
        text += "💍 状态：已婚\n"

    if stats["total"] > 0:
        win_rate = stats["wins"] / stats["total"] * 100
        text += f"\n🎮 游戏统计\n"
        text += f"  ├ 总场次：{stats['total']}\n"
        text += f"  ├ 胜率：{win_rate:.1f}%\n"
        text += f"  └ 总盈亏：{stats['total_profit']:+d}"

    await message.reply(text)


@router.message(Command("rank"))
async def cmd_rank(message: types.Message):
    """积分排行榜"""
    if message.chat.type == "private":
        await message.reply("⚠️ 排行榜仅限群组使用！")
        return

    chat_id = message.chat.id
    rank_data = await redis_db.get_rank(chat_id, top_n=10)

    if not rank_data:
        await message.reply("📊 排行榜还是空的，快来签到吧！")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 积分排行榜 TOP 10\n"]

    for i, (user_id_str, score) in enumerate(rank_data):
        user_id = int(user_id_str)
        user = await sqlite_db.get_user(user_id)
        name = user["first_name"] if user else f"User#{user_id}"
        if user and user["username"]:
            name += f" (@{user['username']})"

        medal = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{medal} {name} — {int(score)} 💎")

    await message.reply("\n".join(lines))