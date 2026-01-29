"""
[INPUT]: 依赖 app.services.twitter, app.services.upstream_api
[OUTPUT]: 对外提供 BaseHandler 抽象基类
[POS]: handlers 模块的基类，被 face_search.py 和 x_roast.py 继承
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from abc import ABC, abstractmethod

from app.services.twitter import TwitterService
from app.services.upstream_api import UpstreamAPIClient


class BaseHandler(ABC):
    def __init__(self, twitter: TwitterService, api_client: UpstreamAPIClient):
        self.twitter = twitter
        self.api = api_client

    @abstractmethod
    async def handle(self, mention: dict, **kwargs) -> dict:
        """处理 mention，返回 {"success": bool, "reply_text": str}"""
