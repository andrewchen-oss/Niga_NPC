"""
[INPUT]: 依赖 httpx, asyncio, app.config
[OUTPUT]: 对外提供 UpstreamAPIClient (face_search, x_roast)
[POS]: services 模块的上游 API 客户端，被 handlers 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import asyncio

import httpx

from app.config import get_settings
from app.utils.logger import logger


class UpstreamAPIClient:
    """wtf.nuwa.world API 客户端"""

    def __init__(self):
        settings = get_settings()
        self.base_url = settings.upstream_api_base_url.rstrip("/")
        self.api_key = settings.upstream_api_key

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def face_search(self, image_bytes: bytes, limit: int = 3, max_retries: int = 3) -> dict:
        """POST /face-search (multipart/form-data, 带重试)"""
        last_error = None

        for attempt in range(max_retries):
            async with httpx.AsyncClient(timeout=120.0) as client:
                try:
                    resp = await client.post(
                        f"{self.base_url}/face-search",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        files={"image": ("image.jpg", image_bytes, "image/jpeg")},
                        data={"limit": str(limit)},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return {"success": True, "results": data.get("results", [])}

                except httpx.HTTPStatusError as e:
                    body = e.response.text[:500]
                    last_error = f"HTTP {e.response.status_code}: {body}"
                    logger.warning(f"Face Search API attempt {attempt + 1}/{max_retries} failed: HTTP {e.response.status_code}")

                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Face Search API attempt {attempt + 1}/{max_retries} failed: {last_error}")

            # ---- 重试前等待 (指数退避) ----
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                await asyncio.sleep(wait_time)

        logger.error(f"Face Search API failed after {max_retries} attempts: {last_error}")
        return {"success": False, "error": last_error}

    async def x_roast(self, handle: str, max_retries: int = 3) -> dict:
        """POST /x-roast (带重试)"""
        last_error = None

        for attempt in range(max_retries):
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    resp = await client.post(
                        f"{self.base_url}/x-roast",
                        headers=self._headers(),
                        json={"handle": handle},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return {"success": True, "roast": data.get("roast", "")}

                except httpx.HTTPStatusError as e:
                    last_error = f"HTTP {e.response.status_code}"
                    logger.warning(f"X Roast API attempt {attempt + 1}/{max_retries} failed: {last_error}")

                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"X Roast API attempt {attempt + 1}/{max_retries} failed: {last_error}")

            # ---- 重试前等待 (指数退避) ----
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                await asyncio.sleep(wait_time)

        logger.error(f"X Roast API failed after {max_retries} attempts: {last_error}")
        return {"success": False, "error": last_error}
