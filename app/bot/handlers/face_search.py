"""
[INPUT]: 依赖 app.services.twitter, app.services.upstream_api, app.bot.response_builder
[OUTPUT]: 对外提供 FaceSearchHandler
[POS]: handlers 模块的人脸搜索处理器，被 processor.py 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import re

from app.services.twitter import TwitterService
from app.services.upstream_api import UpstreamAPIClient
from app.bot.response_builder import ResponseBuilder
from app.utils.logger import logger


def normalize_url(url: str) -> str:
    """清洗上游返回的 URL"""
    if not url:
        return ""

    # ---- 去掉 [数字] 前缀 ----
    url = re.sub(r"^\[\d+\]\s*", "", url.strip())

    # ---- 补全 scheme ----
    if url.startswith("//"):
        url = "https:" + url
    elif not url.startswith(("http://", "https://")):
        url = "https://" + url

    return url


class FaceSearchHandler:
    def __init__(self, twitter: TwitterService, api_client: UpstreamAPIClient):
        self.twitter = twitter
        self.api = api_client

    async def handle(self, mention: dict) -> dict:
        """处理 Face Search 请求"""
        tweet_id = mention["tweet_id"]
        image_urls = mention.get("image_urls", [])

        if not image_urls:
            return {"success": True, "reply_text": ResponseBuilder.no_image()}

        try:
            # ---- 下载图片 → 直接传字节 ----
            image_bytes = await self.twitter.download_image(image_urls[0])

            # ---- 调用上游 API (multipart/form-data) ----
            result = await self.api.face_search(image_bytes, limit=3)

            if not result["success"]:
                logger.error(f"Face Search API failed: {result.get('error')}")
                return {"success": False, "reply_text": ResponseBuilder.error()}

            results = result.get("results", [])

            if not results:
                return {"success": True, "reply_text": ResponseBuilder.no_result()}

            links = [normalize_url(r.get("url", "")) for r in results]
            links = [l for l in links if l]  # 过滤空值

            if not links:
                return {"success": True, "reply_text": ResponseBuilder.no_result()}

            return {
                "success": True,
                "reply_text": ResponseBuilder.face_search_success(links),
            }

        except Exception as e:
            logger.error(f"FaceSearchHandler error: {e}")
            return {"success": False, "reply_text": ResponseBuilder.error()}
