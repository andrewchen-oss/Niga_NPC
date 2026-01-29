"""
[INPUT]: 依赖 app.services.twitter, app.services.upstream_api, app.bot.response_builder
[OUTPUT]: 对外提供 XRoastHandler
[POS]: handlers 模块的用户吐槽处理器，被 processor.py 消费，支持历史注入和复仇模式
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from typing import Optional

from app.services.twitter import TwitterService
from app.services.upstream_api import UpstreamAPIClient
from app.bot.response_builder import ResponseBuilder
from app.utils.logger import logger


class XRoastHandler:
    def __init__(self, twitter: TwitterService, api_client: UpstreamAPIClient):
        self.twitter = twitter
        self.api = api_client

    async def handle(
        self,
        mention: dict,
        target_handle: Optional[str] = None,
        roast_count: int = 0,
        revenge_context: Optional[dict] = None,
    ) -> dict:
        """处理 X Roast 请求，支持历史注入和复仇模式"""
        if not target_handle:
            return {"success": True, "reply_text": ResponseBuilder.no_target()}

        try:
            result = await self.api.x_roast(target_handle)

            if not result["success"]:
                error = result.get("error", "")
                if "not found" in error.lower() or "404" in error:
                    return {"success": True, "reply_text": ResponseBuilder.user_not_found()}

                logger.error(f"X Roast API failed: {error}")
                return {"success": False, "reply_text": ResponseBuilder.error()}

            roast = result.get("roast", "")

            if not roast:
                return {"success": False, "reply_text": ResponseBuilder.error()}

            # ---- 本地后处理增强 ----
            enhanced_roast = self._enhance_roast(
                roast, target_handle, roast_count, revenge_context
            )

            return {
                "success": True,
                "reply_text": ResponseBuilder.roast_success(enhanced_roast, target_handle),
            }

        except Exception as e:
            logger.error(f"XRoastHandler error: {e}")
            return {"success": False, "reply_text": ResponseBuilder.error()}

    def _enhance_roast(
        self,
        roast: str,
        target_handle: str,
        roast_count: int,
        revenge_context: Optional[dict],
    ) -> str:
        """本地后处理增强回复（上游 API 不能改，只能本地加料）"""
        prefix = ""

        # 复仇模式优先级最高
        if revenge_context and revenge_context.get("revenge_mode"):
            attack_count = revenge_context.get("attack_count", 1)
            if attack_count > 1:
                prefix = f"[复仇模式] @{target_handle} 曾喷过你{attack_count}次，现在轮到你了\n\n"
            else:
                prefix = f"[复仇模式] @{target_handle} 曾喷过你，现在轮到你了\n\n"
        # 老朋友模式
        elif roast_count >= 5:
            prefix = f"[老朋友警报] 第{roast_count + 1}次被喷了\n\n"
        elif roast_count >= 2:
            prefix = f"[回头客] 这位又来了，第{roast_count + 1}次\n\n"

        return prefix + roast
