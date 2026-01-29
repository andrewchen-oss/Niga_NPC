"""
[INPUT]: 依赖 fastapi, app.services.oauth_service, app.services.upstream_api, app.db.crud, app.config
[OUTPUT]: 对外提供 OAuth 登录、回调、用户信息、喷人预览 API 端点
[POS]: api/v1 模块的认证 + 用户操作 API
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Response, Cookie, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.config import get_settings
from app.services.oauth_service import XOAuthService
from app.services.upstream_api import UpstreamAPIClient
from app.services.twitter import TwitterService
from app.db.session import get_async_session
from app.db import crud
from app.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["auth"])

# ---- 临时存储 PKCE state (生产环境应该用 Redis) ----
_oauth_states: dict[str, dict] = {}

oauth_service = XOAuthService()
settings = get_settings()


# ============================================================
#  Response Models
# ============================================================

class UserResponse(BaseModel):
    user_id: str
    username: str
    request_count: int
    favorite_targets: list[dict]


class RoastHistoryItem(BaseModel):
    target_handle: str
    roast_text: Optional[str]
    created_at: Optional[str]


class RoastHistoryResponse(BaseModel):
    total: int
    data: list[RoastHistoryItem]


# ============================================================
#  OAuth Endpoints
# ============================================================

@router.get("/twitter")
async def oauth_login():
    """发起 OAuth 登录"""
    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = oauth_service.generate_pkce()

    # 存储 state -> code_verifier 映射
    _oauth_states[state] = {
        "code_verifier": code_verifier,
        "created_at": datetime.utcnow(),
    }

    # 清理过期的 state (超过 10 分钟)
    now = datetime.utcnow()
    expired = [k for k, v in _oauth_states.items() if (now - v["created_at"]).seconds > 600]
    for k in expired:
        del _oauth_states[k]

    auth_url = oauth_service.get_authorization_url(state, code_challenge)
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
):
    """OAuth 回调"""
    # 验证 state
    if state not in _oauth_states:
        logger.error(f"Invalid OAuth state: {state}")
        return RedirectResponse(url=f"{settings.frontend_url}?error=invalid_state")

    code_verifier = _oauth_states.pop(state)["code_verifier"]

    # 换取 token
    token_data = await oauth_service.exchange_code(code, code_verifier)
    if not token_data:
        return RedirectResponse(url=f"{settings.frontend_url}?error=token_exchange_failed")

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    # 获取用户信息
    user_info = await oauth_service.get_user_info(access_token)
    if not user_info:
        return RedirectResponse(url=f"{settings.frontend_url}?error=user_info_failed")

    user_id = user_info.get("id")
    username = user_info.get("username")

    # 更新数据库
    async with get_async_session() as session:
        profile = await crud.get_or_create_requester_profile(session, user_id, username)
        profile.is_registered = True
        profile.oauth_access_token = access_token
        profile.oauth_refresh_token = refresh_token
        profile.last_login_at = datetime.utcnow()
        await session.commit()

    # 生成 JWT
    jwt_token = jwt.encode(
        {
            "user_id": user_id,
            "username": username,
            "exp": datetime.utcnow() + timedelta(days=7),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )

    # 重定向到前端，带上 token
    response = RedirectResponse(url=f"{settings.frontend_url}/dashboard?token={jwt_token}")
    return response


# ============================================================
#  Protected Endpoints
# ============================================================

def verify_token(token: str) -> Optional[dict]:
    """验证 JWT token"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


@router.get("/me", response_model=UserResponse)
async def get_current_user(token: str = Query(...)):
    """获取当前登录用户信息"""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("user_id")

    async with get_async_session() as session:
        profile = await crud.get_requester_profile_by_id(session, user_id)
        if not profile:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
            user_id=profile.user_id,
            username=profile.username,
            request_count=profile.request_count,
            favorite_targets=profile.favorite_targets or [],
        )


@router.get("/me/roasts", response_model=RoastHistoryResponse)
async def get_my_roasts(
    token: str = Query(...),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """获取我的喷人历史"""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("user_id")

    async with get_async_session() as session:
        roasts, total = await crud.get_roasts_by_requester(session, user_id, limit, offset)

        return RoastHistoryResponse(
            total=total,
            data=[
                RoastHistoryItem(
                    target_handle=r.target_handle or "unknown",
                    roast_text=r.reply_text[:200] if r.reply_text else None,
                    created_at=r.created_at.isoformat() if r.created_at else None,
                )
                for r in roasts
            ]
        )


@router.post("/logout")
async def logout():
    """登出（前端清除 token 即可）"""
    return {"message": "Logged out"}


# ============================================================
#  Roast API (Protected)
# ============================================================

class RoastRequest(BaseModel):
    target_handle: str


class RoastResponse(BaseModel):
    success: bool
    target_handle: str
    roast_text: Optional[str] = None
    tweet_id: Optional[str] = None
    tweet_url: Optional[str] = None
    error: Optional[str] = None


@router.post("/roast", response_model=RoastResponse)
async def create_roast(
    request: RoastRequest,
    token: str = Query(...),
):
    """发起喷人请求，Bot 会发推 @ 目标"""
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("user_id")
    username = payload.get("username")
    target = request.target_handle.strip().lstrip("@").lower()

    if not target:
        return RoastResponse(
            success=False,
            target_handle=target,
            error="目标不能为空",
        )

    # 调用上游 API
    api_client = UpstreamAPIClient()
    try:
        result = await api_client.x_roast(target)

        if not result.get("success"):
            error = result.get("error", "Unknown error")
            if "not found" in error.lower() or "404" in error:
                return RoastResponse(
                    success=False,
                    target_handle=target,
                    error="用户不存在",
                )
            return RoastResponse(
                success=False,
                target_handle=target,
                error=error,
            )

        roast = result.get("roast", "")
        if not roast:
            return RoastResponse(
                success=False,
                target_handle=target,
                error="生成失败",
            )

        # 查询历史数据增强
        async with get_async_session() as session:
            profile = await crud.get_roast_profile(session, target)
            roast_count = profile.roast_count if profile else 0

            revenge_ctx = await crud.get_revenge_context(session, target, username)

            # 本地增强
            prefix = ""
            if revenge_ctx and revenge_ctx.get("revenge_mode"):
                attack_count = revenge_ctx.get("attack_count", 1)
                prefix = f"[复仇模式] @{target} 曾喷过你{attack_count}次\n\n"
            elif roast_count >= 5:
                prefix = f"[老朋友警报] 第{roast_count + 1}次被喷\n\n"
            elif roast_count >= 2:
                prefix = f"[回头客] 第{roast_count + 1}次\n\n"

            # 构建推文内容（我 @自己 要喷你 @受害者）
            tweet_text = f"{prefix}我 @{username} 要喷你 @{target}：{roast}"

            # 限制推文长度 (280 字符)
            if len(tweet_text) > 280:
                tweet_text = tweet_text[:277] + "..."

            # 发推
            twitter = TwitterService()
            tweet_result = twitter.post_tweet(tweet_text)
            tweet_id = tweet_result.get("tweet_id")

            # 更新 memory 表
            await crud.update_roast_profile_after_roast(session, target, user_id)
            await crud.update_requester_after_roast(session, user_id, username, target)
            await crud.record_revenge_relation(session, username, target)

        return RoastResponse(
            success=True,
            target_handle=target,
            roast_text=tweet_text,
            tweet_id=tweet_id,
            tweet_url=f"https://x.com/NigaNPC/status/{tweet_id}" if tweet_id else None,
        )

    except Exception as e:
        logger.error(f"Roast API error: {e}")
        return RoastResponse(
            success=False,
            target_handle=target,
            error=f"发送失败: {str(e)}",
        )
