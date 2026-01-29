"""
[INPUT]: 依赖 httpx, app.config
[OUTPUT]: 对外提供 XOAuthService (OAuth 2.0 PKCE 流程)
[POS]: services 模块的 X OAuth 服务
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import secrets
import hashlib
import base64
from urllib.parse import urlencode
from typing import Optional

import httpx

from app.config import get_settings
from app.utils.logger import logger


class XOAuthService:
    """X OAuth 2.0 PKCE 服务"""

    AUTHORIZE_URL = "https://twitter.com/i/oauth2/authorize"
    TOKEN_URL = "https://api.twitter.com/2/oauth2/token"
    USER_INFO_URL = "https://api.twitter.com/2/users/me"

    SCOPES = ["tweet.read", "users.read", "offline.access"]

    def __init__(self):
        self.settings = get_settings()

    def generate_pkce(self) -> tuple[str, str]:
        """生成 PKCE code_verifier 和 code_challenge"""
        code_verifier = secrets.token_urlsafe(64)[:128]
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")
        return code_verifier, code_challenge

    def get_authorization_url(self, state: str, code_challenge: str) -> str:
        """生成 OAuth 授权 URL"""
        params = {
            "response_type": "code",
            "client_id": self.settings.x_client_id,
            "redirect_uri": self.settings.x_callback_url,
            "scope": " ".join(self.SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self.AUTHORIZE_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str, code_verifier: str) -> Optional[dict]:
        """用 code 换取 access_token"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": self.settings.x_callback_url,
                        "code_verifier": code_verifier,
                    },
                    auth=(self.settings.x_client_id, self.settings.x_client_secret),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(f"Token exchange failed: {response.text}")
                    return None

                return response.json()

            except Exception as e:
                logger.error(f"Token exchange error: {e}")
                return None

    async def get_user_info(self, access_token: str) -> Optional[dict]:
        """获取用户信息"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    self.USER_INFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params={"user.fields": "id,username,name,profile_image_url"},
                )

                if response.status_code != 200:
                    logger.error(f"Get user info failed: {response.text}")
                    return None

                data = response.json()
                return data.get("data")

            except Exception as e:
                logger.error(f"Get user info error: {e}")
                return None

    async def refresh_token(self, refresh_token: str) -> Optional[dict]:
        """刷新 access_token"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                    auth=(self.settings.x_client_id, self.settings.x_client_secret),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )

                if response.status_code != 200:
                    logger.error(f"Token refresh failed: {response.text}")
                    return None

                return response.json()

            except Exception as e:
                logger.error(f"Token refresh error: {e}")
                return None
