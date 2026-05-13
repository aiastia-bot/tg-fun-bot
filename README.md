# 🤖 Telegram 娱乐积分 Bot

群组娱乐 + 互动积分系统，适合社群日常活跃。

## ✨ 功能列表

### 📋 签到积分系统
- `/sign` — 每日签到，基础积分 +10
- `/gsign` — 赌博签到，随机积分（可配置范围）
- 连续签到加成（3天×1.5、7天×2、30天×3）
- 已婚用户签到额外 ×1.2 加成

### 🎰 赌博小游戏
- `/dice <金额>` — 掷骰子，大于3赢，赔率1:1
- `/slot <金额>` — 老虎机（三个emoji），全同×10，两个同×2
- `/coin <金额> <正/反>` — 猜正反，赔率1:1
- `/roulette <金额> <红/黑/数字>` — 轮盘
- `/guess <数字>` — 猜数字(1-100)
- `/gift <金额>` — 转赠积分（回复消息）

### 🎴 抽卡系统
- `/draw` — 单抽（50积分）
- `/draw10` — 十连抽（500积分，保底R）
- `/cards` — 查看我的卡片
- 卡片稀有度：⚪N(60%) 🔵R(25%) 🟣SR(12%) 🟡SSR(3%)
- **联动**：稀有卡片给赌局加成赔率

### 💒 社交系统
- `/marry` — 求婚（回复消息，消耗500积分）
- `/divorce` — 离婚（退还一半积分）
- `/couple` — 情侣榜
- **联动**：已婚签到 ×1.2 加成

### 📝 其他功能
- `/hitokoto` — 随机一言（hitokoto.cn API）
- `/hitokoto <分类>` — 分类一言
- `/game` — 2048 小游戏（得分转积分）

### 🔧 工具（私聊）
- `/time` — 当前时间
- `/remind <时间> <内容>` — 定时提醒

### 👮 管理员
- `/setbet <金额>` — 设置下注上限
- `/resetpoints` — 重置积分（回复消息）
- `/broadcast <内容>` — 群公告
- `/chats` — 查看Bot所在群组（超级管理员）

## 🏗️ 技术架构

```
├── main.py              # Bot入口
├── config.py            # 配置管理
├── database/
│   ├── redis_db.py      # Redis存储（积分、签到、排行榜）
│   └── sqlite_db.py     # SQLite存储（用户、记录、卡片）
├── services/
│   ├── sign_service.py  # 签到服务
│   ├── game_service.py  # 赌博游戏服务
│   ├── draw_service.py  # 抽卡服务
│   └── marry_service.py # 结婚服务
├── handlers/
│   ├── sign.py          # 签到/排行榜命令
│   ├── game.py          # 赌博命令
│   ├── draw.py          # 抽卡命令
│   ├── marry.py         # 结婚命令
│   ├── hitokoto.py      # 一言命令
│   ├── tools.py         # 工具/游戏命令
│   └── admin.py         # 管理员命令
├── game/
│   ├── server.py        # 游戏Web服务器
│   └── 2048/
│       └── index.html   # 2048游戏页面
├── Dockerfile
├── docker-compose.yml
└── .github/workflows/   # CI/CD
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo>
cd tg-fun-bot

# 复制配置文件
cp .env.example .env
# 编辑 .env 填写配置
```

### 2. 配置环境变量

```bash
# 必填
BOT_TOKEN=your_bot_token_here

# 超级管理员（Telegram user_id）
SUPER_ADMINS=123456789

# Redis（Docker默认不用改）
REDIS_HOST=redis
REDIS_PORT=6379

# 可选
GAMBLE_SIGN_MIN=-999     # 赌博签到最小值
GAMBLE_SIGN_MAX=30       # 赌博签到最大值
MARRY_COST=500           # 结婚消耗积分
GAME_BASE_URL=http://your-server:8080  # 游戏服务器地址
```

### 3. Docker 部署

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f bot

# 停止
docker-compose down
```

### 4. 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 启动Redis
docker run -d -p 6379:6379 redis:7-alpine

# 启动Bot
python main.py
```

## 🔧 GitHub Actions 配置

在 GitHub 仓库的 Settings → Secrets 中添加：

- `DOCKER_USERNAME` — Docker Hub 用户名
- `DOCKER_PASSWORD` — Docker Hub 密码/Token
- `DOCKER_IMAGE_NAME` — 镜像名称（可选，默认 tg-fun-bot）

推送到 `main` 分支会自动构建并推送 Docker 镜像。

## 📊 Redis Key 设计

```
points:{chat_id}:{user_id}      # 积分（string）
sign:{chat_id}:{user_id}        # 签到日期（string）
streak:{chat_id}:{user_id}      # 连续天数（string）
rank:{chat_id}                  # 排行榜（sorted set）
marry:{chat_id}:{user_id}       # 结婚对象（string）
bet_limit:{chat_id}             # 下注上限（string）
bot_chats                       # 群组列表（hash）
```

## 📝 抽卡系统联动说明

| 卡片类型 | 加成效果 |
|---------|---------|
| 通用加成 | 所有赌局赔率提升 |
| 骰子加成 | `/dice` 赔率提升 |
| 老虎机加成 | `/slot` 赔率提升 |
| 轮盘加成 | `/roulette` 赔率提升 |
| 硬币加成 | `/coin` 赔率提升 |
| 签到加成 | 签到积分提升 |

拥有稀有卡片时，赌局赢钱会额外获得卡片加成的积分。

## 📄 License

MIT