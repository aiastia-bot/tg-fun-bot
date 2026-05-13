import asyncio
import logging
import sys
from datetime import datetime

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties

from config import config
from database.redis_db import redis_db
from database.sqlite_db import sqlite_db
from game.server import create_game_app
from handlers import (
    sign_router,
    game_router,
    draw_router,
    marry_router,
    hitokoto_router,
    tools_router,
    admin_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    """启动命令"""
    await sqlite_db.ensure_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.first_name or "",
    )

    if message.chat.type != "private":
        await redis_db.add_chat(message.chat.id, message.chat.title or "Unknown")

    text = """🤖 欢迎使用娱乐积分Bot！

🎮 这里有签到、赌博、抽卡、结婚等有趣功能！

发送 /help 查看所有命令
发送 /sign 开始每日签到"""

    await message.reply(text)


@dp.message(CommandStart())
async def cmd_start_group(message: Message):
    """群组中的启动"""
    if message.chat.type != "private":
        await redis_db.add_chat(message.chat.id, message.chat.title or "Unknown")


async def check_reminders(bot: Bot):
    """定时检查提醒"""
    while True:
        try:
            reminders = await sqlite_db.get_pending_reminders()
            for reminder in reminders:
                try:
                    await bot.send_message(
                        reminder["user_id"],
                        f"⏰ 提醒！\n\n{reminder['content']}\n\n📅 设置于 {reminder['created_at']}",
                    )
                    await sqlite_db.mark_reminder_sent(reminder["id"])
                except Exception as e:
                    logger.error(f"发送提醒失败: {e}")
        except Exception as e:
            logger.error(f"检查提醒出错: {e}")

        await asyncio.sleep(60)  # 每分钟检查一次


async def main():
    # 检查配置
    if not config.BOT_TOKEN:
        logger.error("请设置 BOT_TOKEN 环境变量！")
        sys.exit(1)

    # 连接数据库
    await redis_db.connect()
    await sqlite_db.connect()
    logger.info("数据库连接成功")

    # 注册路由
    dp.include_router(sign_router)
    dp.include_router(game_router)
    dp.include_router(draw_router)
    dp.include_router(marry_router)
    dp.include_router(hitokoto_router)
    dp.include_router(tools_router)
    dp.include_router(admin_router)

    # 初始化Bot
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # 启动提醒任务
    asyncio.create_task(check_reminders(bot))

    # 启动游戏服务器
    game_app = create_game_app()
    runner = web.AppRunner(game_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("游戏服务器启动: http://0.0.0.0:8080")

    # 启动Bot
    logger.info("Bot 启动成功！")
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await redis_db.close()
        await sqlite_db.close()
        logger.info("Bot 已停止")


if __name__ == "__main__":
    asyncio.run(main())