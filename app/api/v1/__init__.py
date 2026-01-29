"""
[INPUT]: 依赖 app.api.v1.public, app.api.v1.auth
[OUTPUT]: 对外提供 v1_router 汇总路由
[POS]: api/v1 模块的路由聚合层
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from fastapi import APIRouter

from app.api.v1.public import router as public_router
from app.api.v1.auth import router as auth_router

v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(public_router, tags=["public"])
v1_router.include_router(auth_router)
