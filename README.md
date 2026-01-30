# Skyeye Bot

基于 Twitter/X API v2和 Nuwa World API的智能社交回复机器人，支持**人脸识别搜索**和**AI 内容生成**两大核心功能。
唯一支持路径CA（BSC）：0xa8200561e7b1d97589889b1ffcfac091aaa07777（非本人发布）

## 技术栈

- **后端框架**: FastAPI + Uvicorn (异步 ASGI)
- **数据库**: PostgreSQL 16 + SQLAlchemy 2.0 (async)
- **Twitter 集成**: Tweepy + X API v2 Filtered Stream
- **AI 服务**: OpenAI GPT-4o-mini (意图分类)
- **部署**: Docker Compose + Nginx

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Twitter/X Platform                      │
└─────────────────────────┬───────────────────────────────────┘
                          │ Filtered Stream (WebSocket-like)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       Skyeye Bot                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Stream       │  │ Intent       │  │ Response     │       │
│  │ Listener     │──│ Classifier   │──│ Builder      │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                 │                  │               │
│         ▼                 ▼                  ▼               │
│  ┌──────────────────────────────────────────────────┐       │
│  │              Handler Dispatcher                   │       │
│  │   ┌─────────────┐      ┌─────────────┐           │       │
│  │   │ FaceSearch  │      │  X Roast    │           │       │
│  │   │  Handler    │      │  Handler    │           │       │
│  │   └─────────────┘      └─────────────┘           │       │
│  └──────────────────────────────────────────────────┘       │
│                          │                                   │
└──────────────────────────┼───────────────────────────────────┘
                           ▼
              ┌────────────────────────┐
              │   Upstream API Server  │
              │   (wtf.nuwa.world)     │
              │  ┌──────┐  ┌────────┐  │
              │  │Face  │  │Content │  │
              │  │Search│  │Generate│  │
              │  └──────┘  └────────┘  │
              └────────────────────────┘

### 上游 API 服务 (Nuwa.World)

核心 AI 能力由 **[Nuwa.World](https://nuwa.world)** 平台提供：

| 能力 | 说明 |
|------|------|
| **人脸识别搜索** | 基于面部特征的跨平台身份检索，支持全网公开图片匹配 |
| **实时背景信息提取** | 自动抓取目标用户的社交媒体动态、发言历史、互动记录 |
| **社媒信息融合** | 整合 Twitter/X、Instagram 等多平台数据，构建完整用户画像 |
| **AI 内容生成** | 基于用户画像和实时信息，生成个性化、上下文相关的内容 |

本项目作为 Nuwa.World API 的消费端，专注于 Twitter/X 平台的交互层实现。
```

## 核心功能实现

### 1. 实时消息监听 (Filtered Stream)

采用 X API v2 Filtered Stream 实现零延迟消息推送：

```python
# app/bot/stream.py
async def run_stream():
    """长连接监听，实时接收匹配推文"""
    async with client.stream("GET", STREAM_URL, params=params) as response:
        async for line in response.aiter_lines():
            data = json.loads(line)
            mention = parse_stream_tweet(data)
            asyncio.create_task(_process_one(mention, semaphore))
```

**技术要点**:
- 使用 `httpx` 异步流式请求，保持长连接
- 规则过滤: `@BotUsername -is:retweet` 只接收 @ 提及
- 指数退避重连: 5s → 10s → 20s → 60s (上限)
- `asyncio.Semaphore` 控制并发处理数量

### 2. 意图分类 (Intent Classification)

使用 GPT-4o-mini 进行用户意图识别：

```python
# app/services/intent_classifier.py
class IntentClassifier:
    async def classify(self, text: str, has_image: bool) -> IntentResult:
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, ...],
            response_format={"type": "json_object"},
        )
        # 返回: FACE_SEARCH / X_ROAST / UNKNOWN
```

**分类逻辑**:
| 意图 | 触发条件 |
|------|---------|
| `FACE_SEARCH` | 附带图片 + 明确查人关键词 (这是谁、who is this) |
| `X_ROAST` | 用户指挥 Bot 对某人进行评价 |
| `UNKNOWN` | 无法识别的意图，不响应 |

### 3. 人脸搜索 (Face Search API)

**处理流程**:

```
用户发图 → 下载图片 → 调用上游 API → 解析结果 → 回复链接
```

```python
# app/bot/handlers/face_search.py
async def handle(self, mention: dict) -> dict:
    # 1. 下载图片
    image_bytes = await self.twitter.download_image(image_urls[0])

    # 2. 调用上游 Face Search API (multipart/form-data)
    result = await self.api.face_search(image_bytes, limit=3)

    # 3. 返回搜索结果链接
    return {"reply_text": ResponseBuilder.face_search_success(links)}
```

**上游 API 调用**:
```python
# POST /face-search (multipart/form-data)
resp = await client.post(
    f"{base_url}/face-search",
    files={"image": ("image.jpg", image_bytes, "image/jpeg")},
    data={"limit": "3"},
)
```

### 4. AI 内容生成 (X Roast API)

**处理流程**:

```
解析目标用户 → 查询历史记录 → 调用上游 API → 本地增强 → 回复
```

```python
# app/bot/handlers/x_roast.py
async def handle(self, mention, target_handle, roast_count, revenge_context):
    # 1. 调用上游 API 生成内容
    result = await self.api.x_roast(target_handle)

    # 2. 本地后处理增强 (复仇模式 / 老朋友模式)
    enhanced = self._enhance_roast(roast, roast_count, revenge_context)

    return {"reply_text": enhanced}
```

**上游 API 调用**:
```python
# POST /x-roast (application/json)
resp = await client.post(
    f"{base_url}/x-roast",
    json={"handle": target_handle},
)
```

**本地增强逻辑**:
- **复仇模式**: 检测目标用户是否曾对请求者发起过类似请求
- **老朋友模式**: 根据历史记录次数添加特殊前缀

## 数据模型

### 核心表结构

```sql
-- 处理记录 (幂等去重)
CREATE TABLE processed_mentions (
    id UUID PRIMARY KEY,
    tweet_id VARCHAR(64) UNIQUE NOT NULL,
    author_id VARCHAR(64) NOT NULL,
    trigger_type ENUM('face_search', 'x_roast', 'unknown'),
    status ENUM('pending', 'processing', 'completed', 'failed'),
    reply_tweet_id VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);

-- 用户画像 (Long-Term Memory)
CREATE TABLE roast_profiles (
    id UUID PRIMARY KEY,
    target_handle VARCHAR(64) UNIQUE NOT NULL,
    roast_count INTEGER DEFAULT 0,
    unique_roasters INTEGER DEFAULT 0,
    first_roasted_at TIMESTAMP,
    last_roasted_at TIMESTAMP
);

-- 复仇关系
CREATE TABLE revenge_relations (
    attacker_handle VARCHAR(64),
    victim_handle VARCHAR(64),
    attack_count INTEGER DEFAULT 1,
    UNIQUE(attacker_handle, victim_handle)
);
```

## API 端点

### 公开 API

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/stats` | GET | 全局统计数据 |
| `/api/v1/leaderboard` | GET | 排行榜 |
| `/api/v1/profiles/{handle}` | GET | 用户档案 |

### OAuth 认证

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/twitter` | GET | 发起 OAuth 登录 |
| `/api/v1/auth/callback` | GET | OAuth 回调 |
| `/api/v1/auth/me` | GET | 当前用户信息 |
| `/api/v1/auth/roast` | POST | 发起内容生成请求 |

## 可靠性设计

### 1. 幂等处理
```python
# tweet_id 作为唯一键，防止重复处理
if await is_mention_processed(session, tweet_id):
    return  # 跳过已处理的推文
```

### 2. 重试机制
```python
# 指数退避重试 (1s → 2s → 4s)
for attempt in range(max_retries):
    try:
        return await api_call()
    except Exception:
        await asyncio.sleep(2 ** attempt)
```

### 3. 优雅降级
```python
# Stream 连接失败不阻塞启动
stream_ok = await setup_stream_rules()
if not stream_ok:
    logger.warning("Filtered Stream DISABLED")
    # 其他功能继续运行
```

### 4. 反检测延迟
```python
# 随机等待 45-60 秒再回复，模拟人类行为
delay = random.uniform(45, 60)
await asyncio.sleep(delay)
```

## 部署

### Docker Compose

```bash
cd docker
docker-compose --env-file ../.env up -d --build
```

### 环境变量

```env
# Twitter API
TWITTER_API_KEY=xxx
TWITTER_API_SECRET=xxx
TWITTER_BEARER_TOKEN=xxx
TWITTER_ACCESS_TOKEN=xxx
TWITTER_ACCESS_TOKEN_SECRET=xxx
TWITTER_BOT_USER_ID=xxx
TWITTER_BOT_USERNAME=xxx

# 上游 API
UPSTREAM_API_BASE_URL=https://wtf.nuwa.world/api/v1
UPSTREAM_API_KEY=xxx

# OpenAI
OPENAI_API_KEY=xxx

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
```

## 目录结构

```
app/
├── api/           # HTTP 路由层
│   └── v1/        # v1 版本 API (auth, public)
├── bot/           # Bot 核心逻辑
│   ├── stream.py       # Filtered Stream 监听
│   ├── processor.py    # 消息处理分发
│   ├── handlers/       # 功能处理器
│   │   ├── face_search.py
│   │   └── x_roast.py
│   └── response_builder.py
├── db/            # 数据库层
│   ├── models.py       # ORM 模型
│   ├── crud.py         # CRUD 操作
│   └── session.py      # 连接管理
├── services/      # 外部服务封装
│   ├── twitter.py      # Twitter API
│   ├── upstream_api.py # 上游 API
│   └── intent_classifier.py
└── main.py        # 应用入口
```

## License

MIT
