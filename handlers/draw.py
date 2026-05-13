from aiogram import Router, types
from aiogram.filters import Command

from database.redis_db import redis_db
from database.sqlite_db import sqlite_db
from services.draw_service import draw_service

router = Router()


@router.message(Command("draw"))
async def cmd_draw(message: types.Message):
    """单抽"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )

    result = await draw_service.draw(chat_id, user_id)

    if not result["ok"]:
        await message.reply(f"❌ {result['message']}")
        return

    text = f"🎴 抽卡结果\n\n"
    text += f"{result['rarity_emoji']} [{result['card_rarity']}] {result['card_name']}\n"
    text += f"📦 类型：{result['card_type']}\n"

    if result["bonus_type"] and result["bonus_type"] != "无":
        text += f"✨ 加成：{result['bonus_type']} +{result['bonus_value']*100:.0f}%\n"

    text += f"\n💰 消耗：{result['cost']} 积分"
    text += f"\n💎 剩余积分：{result['points']}"

    if result["card_rarity"] in ("SR", "SSR"):
        text += "\n\n🌟 恭喜获得稀有卡片！"

    await message.reply(text)


@router.message(Command("draw10"))
async def cmd_draw10(message: types.Message):
    """十连抽"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )

    result = await draw_service.draw_ten(chat_id, user_id)

    if not result["ok"]:
        await message.reply(f"❌ {result['message']}")
        return

    text = "🎴 十连抽结果\n\n"

    for card in result["cards"]:
        text += f"{card['rarity_emoji']} [{card['card_rarity']}] {card['card_name']}"
        if card["bonus_type"] and card["bonus_type"] != "无":
            text += f" ({card['bonus_type']} +{card['bonus_value']*100:.0f}%)"
        text += "\n"

    # 统计
    summary = {"N": 0, "R": 0, "SR": 0, "SSR": 0}
    for card in result["cards"]:
        summary[card["card_rarity"]] += 1

    text += f"\n📊 统计：⚪N×{summary['N']} 🔵R×{summary['R']} 🟣SR×{summary['SR']} 🟡SSR×{summary['SSR']}"
    text += f"\n\n💰 消耗：{result['cost']} 积分"
    text += f"\n💎 剩余积分：{result['points']}"

    if summary["SSR"] > 0:
        text += "\n\n🎉🎊 超稀有！恭喜！"
    elif summary["SR"] > 0:
        text += "\n\n✨ 不错哦！"

    await message.reply(text)


@router.message(Command("cards"))
async def cmd_cards(message: types.Message):
    """查看我的卡片"""
    chat_id = message.chat.id
    user_id = message.from_user.id

    await sqlite_db.ensure_user(
        user_id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )

    cards = await draw_service.get_my_cards(chat_id, user_id)

    if not cards:
        await message.reply("🎴 你还没有卡片，快去抽卡吧！/draw")
        return

    # 分页显示（最多显示前20张）
    display_cards = cards[:20]

    text = f"🎴 我的卡片 (共{len(cards)}张，显示前20张)\n\n"

    for card in display_cards:
        text += f"{card['rarity_emoji']} [{card['card_rarity']}] {card['card_name']}"
        if card["bonus_type"] and card["bonus_type"] != "无":
            text += f" — {card['bonus_type']} +{card['bonus_value']*100:.0f}%"
        text += "\n"

    summary = draw_service.get_card_summary(cards)
    text += f"\n📊 总计：⚪N×{summary['N']} 🔵R×{summary['R']} 🟣SR×{summary['SR']} 🟡SSR×{summary['SSR']}"

    await message.reply(text)