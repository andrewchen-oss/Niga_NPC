# skyeye-bot - Twitter/X AI Bot (人脸搜索 + 用户吐槽 + 主动开喷)

Python 3.11+ + FastAPI + Tweepy + SQLAlchemy 2.0 + asyncpg + PostgreSQL 16 + httpx + Docker Compose

<directory>
app/         - 应用核心 (5子目录: api, bot, db, services, utils)
  api/       - HTTP 路由层 (健康检查)
  bot/       - Bot 业务核心 (Filtered Stream 监听、Active Roast 主动出击、事件解析、处理、触发词、回复、handlers)
    handlers/ - 功能处理器 (face_search, x_roast)
  db/        - 数据库层 (ORM 模型、CRUD、会话管理)
  services/  - 外部服务封装 (Twitter API, 上游 API)
  utils/     - 工具函数 (日志、图片处理)
alembic/     - 数据库迁移
tests/       - 单元测试
docker/      - Docker 部署配置
scripts/     - 运维脚本
</directory>

<config>
.env.example      - 环境变量模板
requirements.txt  - Python 依赖
pyproject.toml    - 项目元数据 + pytest 配置
alembic.ini       - Alembic 迁移配置
.gitignore        - Git 忽略规则
Jenkinsfile       - CI/CD Pipeline (手动部署到 EC2)
</config>

## 架构决策

- **Filtered Stream 模式**: X API v2 Filtered Stream 实时推送匹配推文，零轮询、零公网暴露
- **Active Roast 模式**: 主动刷 Home Timeline，每 10 分钟随机选一条推文开喷 (配置开关)
- **流式驱动**: 启动 → 设规则 `@bot -is:retweet` → 长连接接收 → 逐条解析分发处理
- **幂等处理**: tweet_id 去重 (DB unique + processor 内检查)
- **自动重连**: 断线指数退避重连 (5s → 10s → 20s → ... → 60s 上限)
- **策略分发**: TriggerParser 解析触发词 → Handler 模式分发到具体处理器
- **抽象人设**: ResponseBuilder 统一管理回复风格（玩梗、简短、抽象）

## 开发规范

- 所有数据库操作走 async/await
- 外部 HTTP 调用使用 httpx AsyncClient
- 新增 Handler 继承 BaseHandler，注册到 processor.py 的分发逻辑
- 环境变量通过 pydantic-settings 统一管理
- Stream 监听在 lifespan 中作为后台 asyncio.create_task 启动
- 处理逻辑受 asyncio.Semaphore 并发限制 (默认 10)

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
