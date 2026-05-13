from datetime import datetime, timedelta
import re

from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import config
from database.sqlite_db import sqlite_db

router = Router()


@router.message(Command("time"))
async def cmd_time(message: types.Message):
    """当前时间"""
    now = datetime.now()
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    weekday = weekdays[now.weekday()]

    await message.reply(
        f"🕐 当前时间\n\n"
        f"📅 日期：{now.strftime('%Y年%m月%d日')}\n"
        f"📆 星期：{weekday}\n"
        f"⏰ 时间：{now.strftime('%H:%M:%S')}\n"
        f"🌍 时间戳：{int(now.timestamp())}"
    )


@router.message(Command("remind"))
async def cmd_remind(message: types.Message):
    """定时提醒（私聊）"""
    if message.chat.type != "private":
        await message.reply("⚠️ 提醒功能仅限私聊使用！")
        return

    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.reply(
            "⏰ 定时提醒\n\n"
            "用法：/remind ＜时间＞ ＜内容＞\n"
            "时间格式：\n"
            "  YYYY-MM-DD HH:MM  如：2025-01-01 08:00\n"
            "  Xm  X分钟后  如：30m（30分钟后）\n"
            "  Xh  X小时后  如：2h（2小时后）\n\n"
            "示例：\n"
            "/remind 2025-01-01 08:00 生日快乐\n"
            "/remind 30m 该喝水了"
        )
        return

    time_str = parts[1]
    content = parts[2]

    # 解析时间
    remind_time = None

    # 相对时间：Xm / Xh
    rel_match = re.match(r"^(\d+)(m|h)$", time_str)
    if rel_match:
        num = int(rel_match.group(1))
        unit = rel_match.group(2)
        if unit == "m":
            remind_time = datetime.now() + timedelta(minutes=num)
        else:
            remind_time = datetime.now() + timedelta(hours=num)
    else:
        # 绝对时间
        try:
            remind_time = datetime.strptime(time_str, "%Y-%m-%d")
        except ValueError:
            try:
                remind_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
            except ValueError:
                await message.reply("❌ 时间格式错误！\n请使用 YYYY-MM-DD 或 YYYY-MM-DD HH:MM 或 Xm/Xh")
                return

    if remind_time <= datetime.now():
        await message.reply("❌ 提醒时间必须在当前时间之后！")
        return

    time_formatted = remind_time.strftime("%Y-%m-%d %H:%M")
    remind_id = await sqlite_db.add_reminder(
        message.from_user.id,
        time_formatted,
        content,
    )

    await message.reply(
        f"⏰ 提醒设置成功！\n\n"
        f"📝 内容：{content}\n"
        f"🕐 时间：{time_formatted}\n"
        f"🆔 提醒ID：{remind_id}"
    )


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    """帮助信息"""
    text = """🤖 Bot 命令列表

📋 签到积分
/sign — 每日签到（+10积分）
/gsign — 赌博签到（随机积分）
/me — 查看个人信息
/rank — 积分排行榜

🎰 赌博小游戏
/dice ＜金额＞ — 掷骰子
/slot ＜金额＞ — 老虎机
/coin ＜金额＞ ＜正/反＞ — 猜正反
/roulette ＜金额＞ ＜红/黑/数字＞ — 轮盘
/guess ＜数字＞ — 猜数字(1-100)
/gift ＜金额＞ — 转赠积分（回复消息）

🎴 抽卡系统
/draw — 单抽(50积分)
/draw10 — 十连抽(500积分)
/cards — 查看我的卡片

💒 社交系统
/marry — 求婚（回复消息）
/divorce — 离婚
/couple — 情侣榜

📝 其他
/hitokoto — 一言
/hitokoto ＜分类＞ — 分类一言
/game — 2048小游戏

🔧 工具（私聊）
/time — 当前时间
/remind ＜时间＞ ＜内容＞ — 定时提醒

👮 管理员
/setbet ＜金额＞ — 设置下注上限
/resetpoints — 重置积分（回复消息）
/broadcast ＜内容＞ — 群公告
/chats — 查看Bot所在群组"""

    await message.reply(text)


@router.message(Command("game"))
async def cmd_game(message: types.Message):
    """2048小游戏"""
    user_id = message.from_user.id
    chat_id = message.chat.id
    game_url = f"{config.GAME_BASE_URL}/2048?user_id={user_id}&chat_id={chat_id}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 开始游戏", url=game_url)],
    ])

    await message.reply(
        "🎮 2048 小游戏\n\n"
        "滑动方块，合并数字，争取达到2048！\n"
        "游戏得分会转换为积分（得分÷10）\n\n"
        "点击下方按钮开始游戏 👇",
        reply_markup=keyboard,
    )
