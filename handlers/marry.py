from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from database.redis_db import redis_db
from database.sqlite_db import sqlite_db
from services.marry_service import marry_service
from config import config

router = Router()


@router.message(Command("marry"))
async def cmd_marry(message: types.Message):
    """求婚"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )

    # 需要回复某人的消息
    if not message.reply_to_message:
        await message.reply("💍 用法：回复某人的消息发送 /marry 向TA求婚\n消耗积分：" + str(config.MARRY_COST))
        return

    to_id = message.reply_to_message.from_user.id
    to_name = message.reply_to_message.from_user.first_name
    from_name = message.from_user.first_name

    await sqlite_db.ensure_user(
        to_id,
        message.reply_to_message.from_user.username or "",
        to_name,
    )

    result = await marry_service.propose(chat_id, user_id, to_id)

    if not result["ok"]:
        await message.reply(f"❌ {result['message']}")
        return

    # 发送求婚消息带按钮
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💕 接受", callback_data=f"marry_accept:{user_id}:{to_id}"),
            InlineKeyboardButton(text="💔 拒绝", callback_data=f"marry_reject:{user_id}:{to_id}"),
        ]
    ])

    await message.reply(
        f"💒 {from_name} 向 {to_name} 求婚了！\n\n"
        f"💰 彩礼：{config.MARRY_COST} 积分\n"
        f"💍 已婚用户签到额外 ×{config.MARRY_SIGN_BONUS} 加成\n\n"
        f"{to_name}，你愿意吗？",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("marry_accept:"))
async def callback_marry_accept(callback: CallbackQuery):
    """接受求婚"""
    parts = callback.data.split(":")
    from_id = int(parts[1])
    to_id = int(parts[2])
    chat_id = callback.message.chat.id

    # 只有被求婚的人才能接受
    if callback.from_user.id != to_id:
        await callback.answer("这不是给你的求婚！", show_alert=True)
        return

    result = await marry_service.accept(chat_id, from_id, to_id)

    if not result["ok"]:
        await callback.answer(result["message"], show_alert=True)
        return

    from_user = await sqlite_db.get_user(from_id)
    to_user = await sqlite_db.get_user(to_id)
    from_name = from_user["first_name"] if from_user else "Unknown"
    to_name = to_user["first_name"] if to_user else "Unknown"

    await callback.message.edit_text(
        f"🎉🎊 恭喜！\n\n"
        f"💒 {from_name} 💕 {to_name}\n"
        f"正式结为夫妻！\n\n"
        f"💰 消耗彩礼：{result['cost']} 积分\n"
        f"✨ 已婚签到加成：×{config.MARRY_SIGN_BONUS}"
    )


@router.callback_query(F.data.startswith("marry_reject:"))
async def callback_marry_reject(callback: CallbackQuery):
    """拒绝求婚"""
    parts = callback.data.split(":")
    from_id = int(parts[1])
    to_id = int(parts[2])
    chat_id = callback.message.chat.id

    if callback.from_user.id != to_id:
        await callback.answer("这不是给你的求婚！", show_alert=True)
        return

    result = await marry_service.reject(chat_id, from_id, to_id)

    if not result["ok"]:
        await callback.answer(result["message"], show_alert=True)
        return

    from_user = await sqlite_db.get_user(from_id)
    from_name = from_user["first_name"] if from_user else "Unknown"
    to_name = callback.from_user.first_name

    await callback.message.edit_text(
        f"💔 {to_name} 拒绝了 {from_name} 的求婚…"
    )


@router.message(Command("divorce"))
async def cmd_divorce(message: types.Message):
    """离婚"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    result = await marry_service.divorce(chat_id, user_id)

    if not result["ok"]:
        await message.reply(f"❌ {result['message']}")
        return

    partner = await sqlite_db.get_user(result["partner_id"])
    partner_name = partner["first_name"] if partner else "Unknown"

    await message.reply(
        f"💔 离婚成功\n\n"
        f"你和 {partner_name} 已解除婚姻关系\n"
        f"💰 退还积分：{result['refund']}"
    )


@router.message(Command("couple"))
async def cmd_couple(message: types.Message):
    """情侣榜"""
    chat_id = message.chat.id
    couples = await marry_service.get_couples_rank(chat_id)

    if not couples:
        await message.reply("💒 情侣榜还是空的，快去求婚吧！/marry")
        return

    text = "💒 情侣榜\n\n"

    for i, couple in enumerate(couples):
        user1 = await sqlite_db.get_user(couple["user1_id"])
        user2 = await sqlite_db.get_user(couple["user2_id"])

        name1 = user1["first_name"] if user1 else "Unknown"
        name2 = user2["first_name"] if user2 else "Unknown"

        medals = ["🥇", "🥈", "🥉"]
        medal = medals[i] if i < 3 else f"{i + 1}."

        text += f"{medal} {name1} 💕 {name2}\n"
        text += f"    结婚于 {couple['created_at'][:10]}\n"

    await message.reply(text)