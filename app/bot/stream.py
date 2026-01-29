"""
[INPUT]: 依赖 httpx, asyncio, app.config, app.bot.event_parser, app.bot.processor,
         app.services.twitter, app.db.session
[OUTPUT]: 对外提供 setup_stream_rules, run_stream 异步函数
[POS]: bot 模块的 Filtered Stream 监听核心，被 main.py lifespan 启动
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import asyncio
import json

import httpx

from app.config import get_settings
from app.bot.event_parser import parse_stream_tweet
from app.bot.processor import process_mention
from app.services.twitter import TwitterService
from app.db.session import get_async_session
from app.utils.logger import logger

# ---- X API v2 Filtered Stream 端点 ----
STREAM_URL = "https://api.x.com/2/tweets/search/stream"
RULES_URL = "https://api.x.com/2/tweets/search/stream/rules"


def _bearer_headers() -> dict:
    """构造 Bearer Token 认证头"""
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.twitter_bearer_token}",
        "User-Agent": "SkyeyeBot/3.0",
    }


# ============================================================
#  规则管理
# ============================================================

async def setup_stream_rules():
    """确保 Filtered Stream 规则为: @bot_username -is:retweet"""
    settings = get_settings()
    headers = _bearer_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # ---- 清理旧规则 ----
        r = await client.get(RULES_URL, headers=headers)
        r.raise_for_status()
        existing = r.json()

        if existing.get("data"):
            ids = [rule["id"] for rule in existing["data"]]
            await client.post(
                RULES_URL,
                headers=headers,
                json={"delete": {"ids": ids}},
            )
            logger.info(f"Deleted {len(ids)} old stream rules")

        # ---- 添加新规则 ----
        rule_value = f"@{settings.twitter_bot_username} -is:retweet"
        resp = await client.post(
            RULES_URL,
            headers=headers,
            json={"add": [{"value": rule_value, "tag": "bot-mention"}]},
        )
        resp.raise_for_status()
        logger.info(f"Stream rule configured: {rule_value}")


# ============================================================
#  流式监听
# ============================================================

async def run_stream():
    """连接 Filtered Stream，持续接收并处理匹配推文"""
    settings = get_settings()
    headers = _bearer_headers()
    semaphore = asyncio.Semaphore(settings.max_concurrent_processing)

    params = {
        "tweet.fields": "created_at,author_id,in_reply_to_user_id,referenced_tweets,attachments,entities",
        "expansions": "author_id,in_reply_to_user_id,attachments.media_keys,referenced_tweets.id,referenced_tweets.id.attachments.media_keys",
        "user.fields": "username",
        "media.fields": "url,type,preview_image_url",
    }

    backoff = 5

    while True:
        try:
            logger.info("Connecting to filtered stream...")
            # ---- 无超时长连接 (keep-alive 每 20s) ----
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(None, connect=30.0),
            ) as client:
                async with client.stream(
                    "GET", STREAM_URL, headers=headers, params=params,
                ) as response:
                    if response.status_code != 200:
                        body = await response.aread()
                        logger.error(
                            f"Stream connect failed: {response.status_code} "
                            f"{body.decode(errors='replace')}"
                        )
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, 60)
                        continue

                    logger.info("Filtered stream connected — listening for mentions")
                    backoff = 5

                    async for line in response.aiter_lines():
                        if not line:
                            continue  # keep-alive blank line

                        try:
                            data = json.loads(line)
                            mention = parse_stream_tweet(
                                data, settings.twitter_bot_user_id,
                            )
                            if mention:
                                asyncio.create_task(
                                    _process_one(mention, semaphore),
                                )
                        except json.JSONDecodeError:
                            continue
                        except Exception as e:
                            logger.error(f"Error handling stream data: {e}")

        except Exception as e:
            logger.error(f"Stream disconnected: {e}")

        logger.info(f"Reconnecting in {backoff}s...")
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)


# ============================================================
#  单条处理 (并发受限于 Semaphore)
# ============================================================

async def _process_one(mention: dict, semaphore: asyncio.Semaphore):
    async with semaphore:
        twitter = TwitterService()
        async with get_async_session() as session:
            try:
                await process_mention(session, twitter, mention)
            except Exception as e:
                logger.error(
                    f"Error processing mention {mention.get('tweet_id')}: {e}",
                )
