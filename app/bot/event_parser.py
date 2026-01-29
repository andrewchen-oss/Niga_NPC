"""
[INPUT]: 无外部依赖，纯逻辑
[OUTPUT]: 对外提供 parse_stream_tweet 函数
[POS]: bot 模块的 v2 Filtered Stream 数据解析器，将流式推文转换为标准 mention 字典
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from app.utils.logger import logger


def parse_stream_tweet(payload: dict, bot_user_id: str) -> dict | None:
    """
    从 Filtered Stream v2 推文中提取标准 mention 字典

    v2 流式数据格式:
    {
        "data": {
            "id": "...", "text": "...", "author_id": "...",
            "in_reply_to_user_id": "...",
            "referenced_tweets": [{"type": "replied_to", "id": "..."}],
            "attachments": {"media_keys": ["..."]},
        },
        "includes": {
            "users": [{"id": "...", "username": "..."}],
            "media": [{"media_key": "...", "type": "photo", "url": "..."}],
        },
        "matching_rules": [{"id": "...", "tag": "..."}]
    }
    """
    data = payload.get("data")
    if not data:
        return None

    author_id = data.get("author_id", "")

    # ---- 过滤 bot 自己发的推文 ----
    if author_id == bot_user_id:
        return None

    includes = payload.get("includes", {})

    # ---- 用户 ID → username 映射 ----
    users_map = {u["id"]: u["username"] for u in includes.get("users", [])}
    author_username = users_map.get(author_id, "unknown")

    # ---- 提取图片 URL (优先当前推文，其次被回复推文) ----
    image_urls = _extract_images(data, includes)
    if not image_urls:
        image_urls = _extract_referenced_images(data, includes)

    # ---- 回复上下文 ----
    reply_to_user_id = data.get("in_reply_to_user_id")
    reply_to_user = users_map.get(reply_to_user_id) if reply_to_user_id else None

    reply_to_tweet_id = None
    for ref in data.get("referenced_tweets", []):
        if ref.get("type") == "replied_to":
            reply_to_tweet_id = ref.get("id")
            break

    # ---- 提取当前推文和父推文的 @mentions ----
    current_mentions = _extract_mentions(data)
    parent_mentions = _extract_parent_mentions(data, includes)
    mentions_with_positions = _extract_mentions_with_positions(data)

    mention = {
        "tweet_id": data.get("id", ""),
        "text": data.get("text", ""),
        "author_id": author_id,
        "author_username": author_username,
        "image_urls": image_urls,
        "created_at": data.get("created_at"),
        "reply_to_user": reply_to_user,
        "reply_to_tweet_id": reply_to_tweet_id,
        "current_mentions": current_mentions,  # 当前推文 @ 的用户
        "parent_mentions": parent_mentions,    # 父推文 @ 的用户
        "mentions_with_positions": mentions_with_positions,  # 带位置信息的 mentions
    }

    logger.debug(
        f"Parsed stream tweet {mention['tweet_id']} "
        f"from @{author_username}"
    )
    return mention


def _extract_mentions(data: dict) -> list[str]:
    """从推文的 entities.mentions 提取 @ 的用户名（小写）"""
    mentions = data.get("entities", {}).get("mentions", [])
    return [m.get("username", "").lower() for m in mentions if m.get("username")]


def _extract_mentions_with_positions(data: dict) -> list[dict]:
    """从推文的 entities.mentions 提取 @ 的用户名和位置信息

    返回格式: [{"username": "xxx", "start": 0, "end": 5}, ...]
    """
    mentions = data.get("entities", {}).get("mentions", [])
    return [
        {
            "username": m.get("username", "").lower(),
            "start": m.get("start", 0),
            "end": m.get("end", 0),
        }
        for m in mentions
        if m.get("username")
    ]


def _extract_parent_mentions(data: dict, includes: dict) -> list[str]:
    """从父推文提取 @ 的用户名（小写）"""
    # ---- 找到被回复的推文 ID ----
    ref_tweet_id = None
    for ref in data.get("referenced_tweets", []):
        if ref.get("type") == "replied_to":
            ref_tweet_id = ref.get("id")
            break

    if not ref_tweet_id:
        return []

    # ---- 从 includes.tweets 找到父推文 ----
    for tweet in includes.get("tweets", []):
        if tweet.get("id") == ref_tweet_id:
            return _extract_mentions(tweet)

    return []


def _extract_images(data: dict, includes: dict) -> list[str]:
    """从 v2 推文中提取图片 URL (支持图片和视频封面)"""
    media_keys = data.get("attachments", {}).get("media_keys", [])
    if not media_keys:
        return []

    media_map = {m["media_key"]: m for m in includes.get("media", [])}
    urls = []

    for key in media_keys:
        if key not in media_map:
            continue

        media = media_map[key]
        media_type = media.get("type")

        # ---- 图片：直接用 url ----
        if media_type == "photo" and media.get("url"):
            urls.append(media["url"])

        # ---- 视频/GIF：用封面图 preview_image_url ----
        elif media_type in ("video", "animated_gif") and media.get("preview_image_url"):
            urls.append(media["preview_image_url"])

    return urls


def _extract_referenced_images(data: dict, includes: dict) -> list[str]:
    """从被回复的推文中提取图片 URL"""
    # ---- 找到被回复的推文 ID ----
    ref_tweet_id = None
    for ref in data.get("referenced_tweets", []):
        if ref.get("type") == "replied_to":
            ref_tweet_id = ref.get("id")
            break

    if not ref_tweet_id:
        return []

    # ---- 从 includes.tweets 找到被回复推文的数据 ----
    ref_tweets = includes.get("tweets", [])
    ref_tweet_data = None
    for tweet in ref_tweets:
        if tweet.get("id") == ref_tweet_id:
            ref_tweet_data = tweet
            break

    if not ref_tweet_data:
        return []

    # ---- 提取被回复推文的图片 ----
    return _extract_images(ref_tweet_data, includes)
