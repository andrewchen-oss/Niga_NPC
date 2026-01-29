"""
[INPUT]: 依赖 fastapi 的 APIRouter
[OUTPUT]: 对外提供 /health 健康检查端点
[POS]: api 模块的健康检查路由
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "skyeye-bot",
    }
