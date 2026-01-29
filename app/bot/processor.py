"""
[INPUT]: 依赖 app.services.twitter, app.services.upstream_api, app.services.intent_classifier,
         app.bot.handlers.*, app.bot.response_builder, app.db.crud, app.db.models
[OUTPUT]: 对外提供 process_mention 异步函数
[POS]: bot 模块的单条 mention 处理核心，被 stream 监听消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import asyncio
import random
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.twitter import TwitterService
from app.services.upstream_api import UpstreamAPIClient
from app.services.intent_classifier import IntentClassifier
from app.db.models import TriggerType
from app.bot.handlers.face_search import FaceSearchHandler
from app.bot.handlers.x_roast import XRoastHandler
from app.bot.response_builder import ResponseBuilder
from app.db.crud import (
    is_mention_processed,
    is_thread_requester_processed,
    create_mention_record,
    update_mention_status,
    get_roast_profile,
    get_revenge_context,
    update_roast_profile_after_roast,
    update_requester_after_roast,
    record_revenge_relation,
)
from app.db.models import ProcessingStatus
from app.config import get_settings
from app.utils.logger import logger


def _extract_target(text: str, bot_username: str, fallback: str | None) -> str | None:
    """从文本中提取 @target（排除 bot 自己）"""
    mentions = re.findall(r"@(\w+)", text, re.IGNORECASE)
    mentions = [m for m in mentions if m.lower() != bot_username.lower()]
    return mentions[0] if mentions else fallback


async def process_mention(
    session: AsyncSession,
    twitter: TwitterService,
    mention: dict,
):
    """处理单条 mention (含幂等去重)"""
    tweet_id = mention["tweet_id"]
    author = mention["author_username"]
    text = mention.get("text", "")

    # ---- 幂等: Webhook 可能重复推送 ----
    if await is_mention_processed(session, tweet_id):
        logger.debug(f"Mention {tweet_id} already processed, skipping")
        return

    logger.info(f"Processing mention {tweet_id} from @{author}")

    settings = get_settings()
    bot_username = settings.twitter_bot_username.lower()
    reply_to_tweet_id = mention.get("reply_to_tweet_id")

    # ---- LLM 意图分类 ----
    has_image = bool(mention.get("image_urls"))
    classifier = IntentClassifier()
    intent_result = await classifier.classify(text, has_image=has_image)

    logger.info(f"Intent: {intent_result.trigger_type.value}, confidence: {intent_result.confidence:.2f}")

    # ---- 提取 target (X_ROAST 用) ----
    target = None
    author_id = mention["author_id"]

    if intent_result.trigger_type == TriggerType.X_ROAST:
        target = _extract_target(text, settings.twitter_bot_username, mention.get("reply_to_user"))

        # ---- C3 去重: 同 thread + 同请求者 只处理一次 ----
        if await is_thread_requester_processed(session, reply_to_tweet_id, author_id):
            logger.info(f"Thread {reply_to_tweet_id} + requester {author_id} already processed, skipping")
            return

    # ---- 创建数据库记录 ----
    await create_mention_record(
        session,
        tweet_id=tweet_id,
        author_id=mention["author_id"],
        author_username=author,
        tweet_text=text,
        trigger_type=intent_result.trigger_type,
        reply_to_tweet_id=reply_to_tweet_id,
        target_handle=target,
    )

    upstream_client = UpstreamAPIClient()

    # ---- 根据意图分发 ----
    try:
        if intent_result.trigger_type == TriggerType.FACE_SEARCH:
            handler = FaceSearchHandler(twitter, upstream_client)
            result = await handler.handle(mention)

        elif intent_result.trigger_type == TriggerType.X_ROAST:
            # ---- 查询历史数据和复仇上下文 ----
            roast_history = await get_roast_profile(session, target) if target else None
            revenge_ctx = await get_revenge_context(session, target, author) if target else None

            handler = XRoastHandler(twitter, upstream_client)
            result = await handler.handle(
                mention,
                target,
                roast_count=roast_history.roast_count if roast_history else 0,
                revenge_context=revenge_ctx,
            )

            # ---- 喷人成功后更新记忆数据 ----
            if result.get("success") and target:
                await update_roast_profile_after_roast(session, target, author_id)
                await update_requester_after_roast(session, author_id, author, target)
                await record_revenge_relation(session, author, target)

        else:
            logger.info(f"Unknown intent for mention {tweet_id}, ignoring")
            await update_mention_status(
                session,
                tweet_id,
                ProcessingStatus.COMPLETED,
                reply_text="[ignored - unknown intent]",
            )
            return

        # ---- 随机延迟 (模拟人类行为，避免被 X 标记) ----
        delay = random.uniform(45, 60)
        logger.info(f"Waiting {delay:.1f}s before replying...")
        await asyncio.sleep(delay)

        # ---- 发送回复 ----
        reply_text = result["reply_text"]
        reply_result = twitter.reply_to_tweet(tweet_id, reply_text)

        await update_mention_status(
            session,
            tweet_id,
            ProcessingStatus.COMPLETED,
            reply_tweet_id=reply_result["reply_tweet_id"],
            reply_text=reply_text,
        )

        logger.info(f"Successfully replied to mention {tweet_id}")

    except Exception as e:
        logger.error(f"Failed to process mention {tweet_id}: {e}")

        await update_mention_status(
            session,
            tweet_id,
            ProcessingStatus.FAILED,
            error_message=str(e),
        )

        try:
            error_reply = ResponseBuilder.error()
            twitter.reply_to_tweet(tweet_id, error_reply)
        except Exception as reply_error:
            logger.error(f"Failed to send error reply: {reply_error}")
