"""轻量级游戏服务器，服务2048等H5游戏并处理分数提交"""
import json
import logging
import os
from aiohttp import web

from database.redis_db import redis_db
from database.sqlite_db import sqlite_db

logger = logging.getLogger(__name__)

GAME_DIR = os.path.join(os.path.dirname(__file__))
GAME_BASE_URL = os.getenv("GAME_BASE_URL", "http://localhost:8080")


async def handle_index(request: web.Request):
    """返回2048游戏页面"""
    user_id = request.query.get("user_id", "0")
    chat_id = request.query.get("chat_id", "0")
    server = GAME_BASE_URL

    with open(os.path.join(GAME_DIR, "2048", "index.html"), "r") as f:
        html = f.read()

    # 注入参数
    html = html.replace(
        "gameServerUrl = null;",
        f'gameServerUrl = "{server}";',
    )
    html = html.replace(
        "userId = null;",
        f"userId = {user_id};",
    )
    html = html.replace(
        "chatId = null;",
        f"chatId = {chat_id};",
    )

    return web.Response(text=html, content_type="text/html")


async def handle_score(request: web.Request):
    """处理游戏分数提交"""
    try:
        data = await request.json()
        user_id = data.get("user_id")
        chat_id = data.get("chat_id")
        game = data.get("game", "unknown")
        score = data.get("score", 0)
        points = data.get("points", 0)

        if not user_id or not chat_id:
            return web.json_response({"ok": False, "message": "参数错误"})

        # 添加积分
        new_points = await redis_db.add_points(chat_id, user_id, points)

        # 记录游戏
        await sqlite_db.add_game_record(
            chat_id, user_id, game, 0,
            f"得分:{score}", points,
        )

        logger.info(f"游戏分数: user={user_id} game={game} score={score} points={points}")

        return web.json_response({
            "ok": True,
            "points": points,
            "total_points": new_points,
        })

    except Exception as e:
        logger.error(f"处理分数失败: {e}")
        return web.json_response({"ok": False, "message": str(e)})


async def handle_health(request: web.Request):
    """健康检查"""
    return web.json_response({"status": "ok"})


def create_game_app() -> web.Application:
    """创建游戏Web应用"""
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/2048", handle_index)
    app.router.add_post("/api/game_score", handle_score)
    app.router.add_get("/api/health", handle_health)
    # 静态文件
    app.router.add_static("/static", os.path.join(GAME_DIR, "2048"))
    return app


def run_game_server(host: str = "0.0.0.0", port: int = 8080):
    """启动游戏服务器"""
    app = create_game_app()
    logger.info(f"游戏服务器启动: http://{host}:{port}")
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_game_server()