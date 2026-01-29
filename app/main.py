"""
[INPUT]: 依赖 app.api.router, app.db.session, app.bot.stream, app.bot.active_roast, app.config, app.utils.logger
[OUTPUT]: 对外提供 FastAPI app 实例
[POS]: 整个应用的入口，初始化数据库、启动 Filtered Stream 监听、启动 Active Roast 调度器、挂载路由、配置 CORS
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import get_settings
from app.db.session import init_db
from app.bot.stream import setup_stream_rules, run_stream
from app.bot.active_roast import run_active_roast
from app.utils.logger import setup_logger, logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- Startup ----
    setup_logger()
    logger.info("Starting Skyeye Bot (Filtered Stream mode)...")

    settings = get_settings()

    await init_db()
    logger.info("Database initialized")

    await setup_stream_rules()
    stream_task = asyncio.create_task(run_stream())
    logger.info("Filtered stream listener launched")

    # ---- Active Roast (主动出击) ----
    active_roast_task = None
    if settings.active_roast_enabled:
        active_roast_task = asyncio.create_task(run_active_roast())
        logger.info("Active Roast scheduler launched")
    else:
        logger.info("Active Roast disabled")

    yield

    # ---- Shutdown ----
    stream_task.cancel()
    if active_roast_task:
        active_roast_task.cancel()
    logger.info("Skyeye Bot shutdown complete")


app = FastAPI(
    title="Skyeye Bot",
    description="Twitter/X AI Bot for Face Search and X Roast (Filtered Stream)",
    version="3.0.0",
    lifespan=lifespan,
)

# ---- CORS 配置 ----
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {"message": "Skyeye Bot is running (Filtered Stream mode)"}
