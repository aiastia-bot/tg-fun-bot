import aiosqlite
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("data/bot.db")


class SQLiteDB:
    def __init__(self):
        self.conn: aiosqlite.Connection | None = None

    async def connect(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(str(DB_PATH))
        self.conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        if self.conn:
            await self.conn.close()

    async def _create_tables(self):
        await self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT DEFAULT '',
                first_name TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS game_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                game_type TEXT NOT NULL,
                bet_amount INTEGER DEFAULT 0,
                result TEXT DEFAULT '',
                profit INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                card_name TEXT NOT NULL,
                card_rarity TEXT NOT NULL,
                card_type TEXT NOT NULL,
                bonus_type TEXT DEFAULT '',
                bonus_value REAL DEFAULT 0,
                obtained_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS marriages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                active INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                remind_time TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                sent INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_game_records_user ON game_records(chat_id, user_id);
            CREATE INDEX IF NOT EXISTS idx_cards_user ON cards(chat_id, user_id);
            CREATE INDEX IF NOT EXISTS idx_marriages_chat ON marriages(chat_id, active);
            CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id, sent);
        """)
        await self.conn.commit()

    # ========== 用户 ==========

    async def ensure_user(self, user_id: int, username: str = "", first_name: str = ""):
        """确保用户存在"""
        await self.conn.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name),
        )
        # 更新用户名
        if username:
            await self.conn.execute(
                "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                (username, first_name, user_id),
            )
        await self.conn.commit()

    async def get_user(self, user_id: int) -> dict | None:
        """获取用户信息"""
        cursor = await self.conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    # ========== 游戏记录 ==========

    async def add_game_record(
        self, chat_id: int, user_id: int,
        game_type: str, bet_amount: int,
        result: str, profit: int
    ):
        """添加游戏记录"""
        await self.conn.execute(
            "INSERT INTO game_records (chat_id, user_id, game_type, bet_amount, result, profit) VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, user_id, game_type, bet_amount, result, profit),
        )
        await self.conn.commit()

    async def get_game_stats(self, chat_id: int, user_id: int) -> dict:
        """获取用户游戏统计"""
        cursor = await self.conn.execute(
            "SELECT COUNT(*) as total, SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as wins, SUM(profit) as total_profit FROM game_records WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        row = await cursor.fetchone()
        if row and row["total"]:
            return {
                "total": row["total"],
                "wins": row["wins"] or 0,
                "total_profit": row["total_profit"] or 0,
            }
        return {"total": 0, "wins": 0, "total_profit": 0}

    # ========== 卡片 ==========

    async def add_card(
        self, chat_id: int, user_id: int,
        card_name: str, card_rarity: str,
        card_type: str, bonus_type: str = "",
        bonus_value: float = 0
    ) -> int:
        """添加卡片，返回卡片ID"""
        cursor = await self.conn.execute(
            "INSERT INTO cards (chat_id, user_id, card_name, card_rarity, card_type, bonus_type, bonus_value) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chat_id, user_id, card_name, card_rarity, card_type, bonus_type, bonus_value),
        )
        await self.conn.commit()
        return cursor.lastrowid

    async def get_user_cards(self, chat_id: int, user_id: int) -> list[dict]:
        """获取用户所有卡片"""
        cursor = await self.conn.execute(
            "SELECT * FROM cards WHERE chat_id = ? AND user_id = ? ORDER BY obtained_at DESC",
            (chat_id, user_id),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_best_bonus_card(self, chat_id: int, user_id: int, bonus_type: str) -> dict | None:
        """获取用户最佳的加成卡片"""
        cursor = await self.conn.execute(
            "SELECT * FROM cards WHERE chat_id = ? AND user_id = ? AND bonus_type = ? ORDER BY bonus_value DESC LIMIT 1",
            (chat_id, user_id, bonus_type),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    # ========== 婚姻记录 ==========

    async def add_marriage(self, chat_id: int, user1_id: int, user2_id: int):
        """添加婚姻记录"""
        await self.conn.execute(
            "INSERT INTO marriages (chat_id, user1_id, user2_id) VALUES (?, ?, ?)",
            (chat_id, user1_id, user2_id),
        )
        await self.conn.commit()

    async def deactivate_marriage(self, chat_id: int, user_id: int):
        """解除婚姻"""
        await self.conn.execute(
            "UPDATE marriages SET active = 0 WHERE chat_id = ? AND (user1_id = ? OR user2_id = ?) AND active = 1",
            (chat_id, user_id, user_id),
        )
        await self.conn.commit()

    async def get_couples(self, chat_id: int, limit: int = 10) -> list[dict]:
        """获取情侣榜"""
        cursor = await self.conn.execute(
            "SELECT * FROM marriages WHERE chat_id = ? AND active = 1 ORDER BY created_at ASC LIMIT ?",
            (chat_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    # ========== 提醒 ==========

    async def add_reminder(self, user_id: int, remind_time: str, content: str) -> int:
        """添加提醒"""
        cursor = await self.conn.execute(
            "INSERT INTO reminders (user_id, remind_time, content) VALUES (?, ?, ?)",
            (user_id, remind_time, content),
        )
        await self.conn.commit()
        return cursor.lastrowid

    async def get_pending_reminders(self) -> list[dict]:
        """获取所有待发送的提醒"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor = await self.conn.execute(
            "SELECT * FROM reminders WHERE sent = 0 AND remind_time <= ?",
            (now,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def mark_reminder_sent(self, reminder_id: int):
        """标记提醒已发送"""
        await self.conn.execute(
            "UPDATE reminders SET sent = 1 WHERE id = ?",
            (reminder_id,),
        )
        await self.conn.commit()


sqlite_db = SQLiteDB()