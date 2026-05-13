from aiogram import Router, types
from aiogram.filters import Command

from config import config
from database.redis_db import redis_db
from database.sqlite_db import sqlite_db

router = Router()


def is_admin(user_id: int) -> bool:
    """检查是否为超级管理员"""
    return user_id in config.SUPER_ADMINS


@router.message(Command("setbet"))
async def cmd_setbet(message: types.Message):
    """设置下注上限（管理员）"""
    if not is_admin(message.from_user.id):
        await message.reply("❌ 你没有管理员权限！")
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.reply("用法：/setbet <金额>\n0 = 不限制")
        return

    try:
        limit = int(parts[1])
    except ValueError:
        await message.reply("金额必须是数字！")
        return

    chat_id = message.chat.id
    await redis_db.set_bet_limit(chat_id, limit)

    if limit == 0:
        await message.reply("✅ 已取消下注上限")
    else:
        await message.reply(f"✅ 下注上限已设置为 {limit} 💎")


@router.message(Command("resetpoints"))
async def cmd_resetpoints(message: types.Message):
    """重置积分（管理员）"""
    if not is_admin(message.from_user.id):
        await message.reply("❌ 你没有管理员权限！")
        return

    if not message.reply_to_message:
        await message.reply("用法：回复某人的消息发送 /resetpoints")
        return

    chat_id = message.chat.id
    target_id = message.reply_to_message.from_user.id
    target_name = message.reply_to_message.from_user.first_name

    await redis_db.set_points(chat_id, target_id, 0)

    await message.reply(f"✅ 已重置 {target_name} 的积分为 0")


@router.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    """群公告（管理员）"""
    if not is_admin(message.from_user.id):
        await message.reply("❌ 你没有管理员权限！")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("用法：/broadcast <内容>")
        return

    content = parts[1]
    await message.reply(f"📢 群公告\n\n{content}")


@router.message(Command("chats"))
async def cmd_chats(message: types.Message):
    """查看Bot所在群组（超级管理员）"""
    if not is_admin(message.from_user.id):
        await message.reply("❌ 你没有管理员权限！")
        return

    chats = await redis_db.get_all_chats()

    if not chats:
        await message.reply("Bot 还没有加入任何群组")
        return

    text = f"📋 Bot所在群组 ({len(chats)}个)\n\n"
    for chat_id, chat_title in chats.items():
        text += f"• {chat_title} ({chat_id})\n"

    await message.reply(text)