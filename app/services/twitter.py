"""
[INPUT]: 依赖 tweepy, httpx, app.config
[OUTPUT]: 对外提供 TwitterService (reply_to_tweet, download_image, get_home_timeline)
[POS]: services 模块的 Twitter API 封装层，被 processor/handlers 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import tweepy
import httpx

from app.config import get_settings
from app.utils.logger import logger


class TwitterService:
    def __init__(self):
        settings = get_settings()

        self.client = tweepy.Client(
            bearer_token=settings.twitter_bearer_token,
            consumer_key=settings.twitter_api_key,
            consumer_secret=settings.twitter_api_secret,
            access_token=settings.twitter_access_token,
            access_token_secret=settings.twitter_access_token_secret,
            wait_on_rate_limit=True,
        )

        self.bot_user_id = settings.twitter_bot_user_id

    def reply_to_tweet(self, tweet_id: str, text: str) -> dict:
        """回复推文"""
        try:
            response = self.client.create_tweet(
                text=text,
                in_reply_to_tweet_id=tweet_id,
            )
            return {
                "reply_tweet_id": str(response.data["id"]),
                "text": text,
            }
        except tweepy.errors.Forbidden as e:
            # ---- 详细记录 403 错误原因 ----
            error_detail = f"403 Forbidden for tweet {tweet_id}"
            if hasattr(e, 'api_errors') and e.api_errors:
                error_detail += f" | API errors: {e.api_errors}"
            if hasattr(e, 'api_messages') and e.api_messages:
                error_detail += f" | Messages: {e.api_messages}"
            if hasattr(e, 'response') and e.response:
                try:
                    error_detail += f" | Response: {e.response.text[:500]}"
                except:
                    pass
            logger.error(error_detail)
            raise
        except tweepy.errors.TweepyException as e:
            logger.error(f"Tweepy error for tweet {tweet_id}: {type(e).__name__} - {e}")
            raise

    def post_tweet(self, text: str) -> dict:
        """发送新推文"""
        response = self.client.create_tweet(text=text)
        return {
            "tweet_id": str(response.data["id"]),
            "text": text,
        }

    async def download_image(self, url: str) -> bytes:
        """下载图片"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content

    def get_home_timeline(self, max_results: int = 20) -> list[dict]:
        """
        获取 Bot 账号的 Home Timeline
        返回标准化的推文列表，每条包含:
        - tweet_id, text, author_id, author_username, is_retweet, in_reply_to_user_id
        """
        try:
            response = self.client.get_home_timeline(
                max_results=max_results,
                tweet_fields=["author_id", "created_at", "referenced_tweets", "in_reply_to_user_id"],
                user_fields=["username"],
                expansions=["author_id"],
            )

            if not response.data:
                return []

            # ---- 构建 author_id → username 映射 ----
            user_map = {}
            if response.includes and "users" in response.includes:
                for user in response.includes["users"]:
                    user_map[user.id] = user.username

            # ---- 转换为标准格式 ----
            tweets = []
            for tweet in response.data:
                is_retweet = False
                if tweet.referenced_tweets:
                    is_retweet = any(ref.type == "retweeted" for ref in tweet.referenced_tweets)

                tweets.append({
                    "tweet_id": str(tweet.id),
                    "text": tweet.text,
                    "author_id": str(tweet.author_id),
                    "author_username": user_map.get(tweet.author_id, ""),
                    "is_retweet": is_retweet,
                    "in_reply_to_user_id": str(tweet.in_reply_to_user_id) if tweet.in_reply_to_user_id else None,
                })

            return tweets

        except Exception as e:
            logger.error(f"Failed to get home timeline: {e}")
            return []
