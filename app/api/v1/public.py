"""
[INPUT]: 依赖 app.db.session, app.db.models, app.db.crud
[OUTPUT]: 对外提供排行榜、档案、统计 API 端点
[POS]: api/v1 模块的公开 API，无需认证
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.db.session import get_async_session
from app.db import crud

router = APIRouter()


# ============================================================
#  Response Models
# ============================================================

class LeaderboardItem(BaseModel):
    rank: int
    handle: str
    roast_count: int
    unique_roasters: int
    last_roasted_at: Optional[str] = None


class LeaderboardResponse(BaseModel):
    total: int
    data: list[LeaderboardItem]


class ProfileResponse(BaseModel):
    handle: str
    roast_count: int
    unique_roasters: int
    first_roasted_at: Optional[str] = None
    last_roasted_at: Optional[str] = None
    roast_themes: list[str]
    recent_roasts: list[dict]


class StatsResponse(BaseModel):
    total_roasts: int
    total_targets: int
    total_requesters: int
    top_victim: Optional[dict] = None
    top_roaster: Optional[dict] = None


# ============================================================
#  Endpoints
# ============================================================

@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """获取被喷排行榜"""
    async with get_async_session() as session:
        profiles, total = await crud.get_roast_leaderboard(session, limit, offset)

        return LeaderboardResponse(
            total=total,
            data=[
                LeaderboardItem(
                    rank=offset + i + 1,
                    handle=p.target_handle,
                    roast_count=p.roast_count,
                    unique_roasters=p.unique_roasters,
                    last_roasted_at=p.last_roasted_at.isoformat() if p.last_roasted_at else None,
                )
                for i, p in enumerate(profiles)
            ]
        )


@router.get("/profiles/{handle}", response_model=ProfileResponse)
async def get_profile(handle: str):
    """获取单个用户的被喷档案"""
    async with get_async_session() as session:
        profile = await crud.get_roast_profile(session, handle.lower())

        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        recent_roasts = await crud.get_recent_roasts_for_target(session, handle.lower(), limit=10)

        return ProfileResponse(
            handle=profile.target_handle,
            roast_count=profile.roast_count,
            unique_roasters=profile.unique_roasters,
            first_roasted_at=profile.first_roasted_at.isoformat() if profile.first_roasted_at else None,
            last_roasted_at=profile.last_roasted_at.isoformat() if profile.last_roasted_at else None,
            roast_themes=profile.roast_themes or [],
            recent_roasts=recent_roasts,
        )


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """获取全局统计数据"""
    async with get_async_session() as session:
        stats = await crud.get_global_stats(session)
        return StatsResponse(**stats)
