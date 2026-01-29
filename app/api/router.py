"""
[INPUT]: 依赖 app.api.health, app.api.v1
[OUTPUT]: 对外提供 api_router 汇总路由
[POS]: api 模块的路由聚合层
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from fastapi import APIRouter

from app.api.health import router as health_router
from app.api.v1 import v1_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(v1_router)
