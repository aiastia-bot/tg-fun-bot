from handlers.sign import router as sign_router
from handlers.game import router as game_router
from handlers.draw import router as draw_router
from handlers.marry import router as marry_router
from handlers.hitokoto import router as hitokoto_router
from handlers.tools import router as tools_router
from handlers.admin import router as admin_router

__all__ = [
    "sign_router",
    "game_router",
    "draw_router",
    "marry_router",
    "hitokoto_router",
    "tools_router",
    "admin_router",
]