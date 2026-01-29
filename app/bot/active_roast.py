"""
[INPUT]: 依赖 app.config, app.services.twitter, app.services.upstream_api, app.db.session, app.db.crud
[OUTPUT]: 对外提供 run_active_roast 主循环
[POS]: bot 模块的主动出击调度器，与 stream.py 并行运行，在 main.py lifespan 中启动
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import asyncio
import random

from app.config import get_settings
from app.services.twitter import TwitterService
from app.services.upstream_api import UpstreamAPIClient
from app.bot.response_builder import ResponseBuilder
from app.db.session import get_async_session
from app.db.crud import is_tweet_roasted, create_roast_record
from app.utils.logger import logger


# ============================================================
#  候选推文筛选
# ============================================================

async def filter_candidates(tweets: list[dict], bot_user_id: str) -> list[dict]:
    """
    筛选可以喷的推文，排除:
    1. Bot 自己的推文
    2. 转推
    3. 回复其他人的推文
    4. 已喷过的推文
    """
    if not tweets:
        return []

    candidates = []

    async with get_async_session() as session:
        for tweet in tweets:
            # ---- 排除自己 ----
            if tweet["author_id"] == bot_user_id:
                continue

            # ---- 排除转推 ----
            if tweet.get("is_retweet"):
                continue

            # ---- 排除回复贴 ----
            if tweet.get("in_reply_to_user_id"):
                continue

            # ---- 排除已喷过 ----
            if await is_tweet_roasted(session, tweet["tweet_id"]):
                continue

            candidates.append(tweet)

    return candidates


# ============================================================
#  主循环
# ============================================================

async def run_active_roast():
    """
    主动刷 Home Timeline 并随机开喷
    间隔: 10 分钟 ± 随机抖动
    """
    settings = get_settings()

    if not settings.active_roast_enabled:
        logger.info("Active Roast disabled, skipping...")
        return

    twitter = TwitterService()
    upstream = UpstreamAPIClient()

    base_interval = settings.active_roast_interval
    jitter = settings.active_roast_jitter

    logger.info(f"Active Roast started (interval={base_interval}s, jitter=±{jitter}s)")

    while True:
        try:
            # ---- 计算本轮等待时间 ----
            wait_time = base_interval + random.randint(-jitter, jitter)
            logger.debug(f"Active Roast sleeping for {wait_time}s")
            await asyncio.sleep(wait_time)

            # ---- 获取 Home Timeline ----
            logger.debug("Fetching home timeline...")
            tweets = twitter.get_home_timeline(max_results=20)

            if not tweets:
                logger.debug("No tweets in home timeline, skipping...")
                continue

            # ---- 筛选候选 ----
            candidates = await filter_candidates(tweets, twitter.bot_user_id)

            if not candidates:
                logger.debug("No valid candidates after filtering, skipping...")
                continue

            # ---- 随机选择目标 ----
            target = random.choice(candidates)
            target_username = target["author_username"]
            tweet_id = target["tweet_id"]

            logger.info(f"Active Roast target: @{target_username} (tweet_id={tweet_id})")

            # ---- 调用 x_roast API ----
            result = await upstream.x_roast(target_username)

            if not result["success"]:
                logger.warning(f"x_roast API failed for @{target_username}: {result.get('error')}")
                continue

            roast_text = result.get("roast", "")
            if not roast_text:
                logger.warning(f"Empty roast for @{target_username}, skipping...")
                continue

            # ---- 构建回复 (@ 目标用户) ----
            reply_text = ResponseBuilder.roast_success(roast_text, target_username)

            # ---- 发送回复 ----
            try:
                reply_result = twitter.reply_to_tweet(tweet_id, reply_text)
                reply_tweet_id = reply_result.get("reply_tweet_id")
                logger.info(f"Active Roast sent: reply_id={reply_tweet_id}")
            except Exception as e:
                logger.error(f"Failed to send active roast reply: {e}")
                continue

            # ---- 记录到数据库 ----
            async with get_async_session() as session:
                await create_roast_record(
                    session=session,
                    tweet_id=tweet_id,
                    author_id=target["author_id"],
                    author_username=target_username,
                    roast_content=roast_text,
                    reply_tweet_id=reply_tweet_id,
                )

            logger.info(f"Active Roast completed for @{target_username}")

        except asyncio.CancelledError:
            logger.info("Active Roast task cancelled")
            break
        except Exception as e:
            logger.error(f"Active Roast error: {e}")
            # 出错后等待一段时间再继续，避免死循环
            await asyncio.sleep(60)
