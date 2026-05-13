import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Telegram Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))

    # 超级管理员
    SUPER_ADMINS: list[int] = [
        int(x.strip())
        for x in os.getenv("SUPER_ADMINS", "").split(",")
        if x.strip().isdigit()
    ]

    # 赌博签到范围
    GAMBLE_SIGN_MIN: int = int(os.getenv("GAMBLE_SIGN_MIN", -999))
    GAMBLE_SIGN_MAX: int = int(os.getenv("GAMBLE_SIGN_MAX", 30))

    # 结婚消耗积分
    MARRY_COST: int = int(os.getenv("MARRY_COST", 500))

    # 下注上限
    DEFAULT_BET_LIMIT: int = int(os.getenv("DEFAULT_BET_LIMIT", 0))

    # 游戏服务器地址
    GAME_BASE_URL: str = os.getenv("GAME_BASE_URL", "http://localhost:8080")

    # 抽卡消耗积分
    DRAW_COST: int = 50

    # 签到基础积分
    SIGN_BASE_POINTS: int = 10

    # 连续签到加成
    STREAK_BONUS: dict[int, float] = {
        3: 1.5,
        7: 2.0,
        30: 3.0,
    }

    # 已婚签到加成
    MARRY_SIGN_BONUS: float = 1.2


config = Config()