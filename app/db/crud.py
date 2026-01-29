"""
[INPUT]: 依赖 app.db.models 的 ProcessedMention, ProcessingStatus, TriggerType, ActiveRoastRecord, RoastProfile, RequesterProfile, RevengeRelation
[OUTPUT]: 对外提供 mention CRUD, active_roast CRUD, profile CRUD, leaderboard/stats 查询
[POS]: db 模块的 CRUD 操作层，被 processor 和 API 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from typing import Optional
from datetime import datetime

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ProcessedMention,
    ProcessingStatus,
    TriggerType,
    ActiveRoastRecord,
    RoastProfile,
    RequesterProfile,
    RevengeRelation,
)


async def is_mention_processed(session: AsyncSession, tweet_id: str) -> bool:
    """检查 mention 是否已处理"""
    result = await session.execute(
        select(ProcessedMention).where(ProcessedMention.tweet_id == tweet_id)
    )
    return result.scalar_one_or_none() is not None


async def is_thread_requester_processed(
    session: AsyncSession,
    reply_to_tweet_id: Optional[str],
    author_id: str,
) -> bool:
    """检查同一 thread 下的同一请求者是否已触发过 (C3 去重)"""
    if not reply_to_tweet_id:
        return False

    result = await session.execute(
        select(ProcessedMention).where(
            ProcessedMention.reply_to_tweet_id == reply_to_tweet_id,
            ProcessedMention.author_id == author_id,
            ProcessedMention.trigger_type == TriggerType.X_ROAST,
            ProcessedMention.status == ProcessingStatus.COMPLETED,
        )
    )
    return result.scalar_one_or_none() is not None


async def create_mention_record(
    session: AsyncSession,
    tweet_id: str,
    author_id: str,
    author_username: str,
    tweet_text: str,
    trigger_type: TriggerType,
    reply_to_tweet_id: Optional[str] = None,
    target_handle: Optional[str] = None,
) -> ProcessedMention:
    """创建 mention 处理记录"""
    record = ProcessedMention(
        tweet_id=tweet_id,
        author_id=author_id,
        author_username=author_username,
        tweet_text=tweet_text,
        trigger_type=trigger_type,
        status=ProcessingStatus.PROCESSING,
        reply_to_tweet_id=reply_to_tweet_id,
        target_handle=target_handle.lower() if target_handle else None,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def update_mention_status(
    session: AsyncSession,
    tweet_id: str,
    status: ProcessingStatus,
    reply_tweet_id: Optional[str] = None,
    reply_text: Optional[str] = None,
    error_message: Optional[str] = None,
):
    """更新 mention 处理状态"""
    result = await session.execute(
        select(ProcessedMention).where(ProcessedMention.tweet_id == tweet_id)
    )
    record = result.scalar_one_or_none()

    if record:
        record.status = status
        record.processed_at = datetime.utcnow()

        if reply_tweet_id:
            record.reply_tweet_id = reply_tweet_id
        if reply_text:
            record.reply_text = reply_text
        if error_message:
            record.error_message = error_message

        await session.commit()


# ============================================================
#  Active Roast CRUD
# ============================================================

async def is_tweet_roasted(session: AsyncSession, tweet_id: str) -> bool:
    """检查推文是否已被主动喷过"""
    result = await session.execute(
        select(ActiveRoastRecord).where(ActiveRoastRecord.tweet_id == tweet_id)
    )
    return result.scalar_one_or_none() is not None


async def create_roast_record(
    session: AsyncSession,
    tweet_id: str,
    author_id: str,
    author_username: str,
    roast_content: str,
    reply_tweet_id: Optional[str] = None,
) -> ActiveRoastRecord:
    """创建主动 Roast 记录"""
    record = ActiveRoastRecord(
        tweet_id=tweet_id,
        author_id=author_id,
        author_username=author_username,
        roast_content=roast_content,
        reply_tweet_id=reply_tweet_id,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


# ============================================================
#  RoastProfile CRUD (排行榜 & 档案)
# ============================================================

async def get_roast_leaderboard(
    session: AsyncSession,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[RoastProfile], int]:
    """获取被喷排行榜"""
    # 总数
    count_result = await session.execute(select(func.count(RoastProfile.id)))
    total = count_result.scalar() or 0

    # 排行榜数据
    result = await session.execute(
        select(RoastProfile)
        .order_by(desc(RoastProfile.roast_count))
        .offset(offset)
        .limit(limit)
    )
    profiles = result.scalars().all()

    return list(profiles), total


async def get_roast_profile(session: AsyncSession, handle: str) -> Optional[RoastProfile]:
    """获取单个用户的被喷档案"""
    result = await session.execute(
        select(RoastProfile).where(RoastProfile.target_handle == handle.lower())
    )
    return result.scalar_one_or_none()


async def get_or_create_roast_profile(session: AsyncSession, handle: str) -> RoastProfile:
    """获取或创建被喷者档案"""
    profile = await get_roast_profile(session, handle)
    if not profile:
        profile = RoastProfile(target_handle=handle.lower())
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


async def update_roast_profile_after_roast(
    session: AsyncSession,
    target_handle: str,
    requester_id: str,
) -> RoastProfile:
    """喷人后更新被喷者档案"""
    profile = await get_or_create_roast_profile(session, target_handle)

    # 更新统计
    profile.roast_count += 1
    profile.last_roasted_at = datetime.utcnow()

    if not profile.first_roasted_at:
        profile.first_roasted_at = datetime.utcnow()

    # 检查是否是新的喷人者
    existing_roasters = await session.execute(
        select(func.count(func.distinct(ProcessedMention.author_id)))
        .where(
            ProcessedMention.target_handle == target_handle.lower(),
            ProcessedMention.trigger_type == TriggerType.X_ROAST,
            ProcessedMention.status == ProcessingStatus.COMPLETED,
        )
    )
    profile.unique_roasters = existing_roasters.scalar() or 0

    await session.commit()
    await session.refresh(profile)
    return profile


async def get_recent_roasts_for_target(
    session: AsyncSession,
    handle: str,
    limit: int = 10,
) -> list[dict]:
    """获取某用户最近被喷的记录"""
    result = await session.execute(
        select(ProcessedMention)
        .where(
            ProcessedMention.target_handle == handle.lower(),
            ProcessedMention.trigger_type == TriggerType.X_ROAST,
            ProcessedMention.status == ProcessingStatus.COMPLETED,
        )
        .order_by(desc(ProcessedMention.created_at))
        .limit(limit)
    )
    mentions = result.scalars().all()

    return [
        {
            "roaster": m.author_username,
            "text": m.reply_text[:200] if m.reply_text else None,
            "at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in mentions
    ]


# ============================================================
#  RequesterProfile CRUD (请求者画像)
# ============================================================

async def get_or_create_requester_profile(
    session: AsyncSession,
    user_id: str,
    username: str,
) -> RequesterProfile:
    """获取或创建请求者画像"""
    result = await session.execute(
        select(RequesterProfile).where(RequesterProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = RequesterProfile(user_id=user_id, username=username)
        session.add(profile)
        await session.commit()
        await session.refresh(profile)

    return profile


async def update_requester_after_roast(
    session: AsyncSession,
    user_id: str,
    username: str,
    target_handle: str,
) -> RequesterProfile:
    """喷人后更新请求者画像"""
    profile = await get_or_create_requester_profile(session, user_id, username)

    profile.request_count += 1

    # 更新 favorite_targets
    targets = profile.favorite_targets or []
    found = False
    for t in targets:
        if t.get("handle") == target_handle.lower():
            t["count"] = t.get("count", 0) + 1
            found = True
            break
    if not found:
        targets.append({"handle": target_handle.lower(), "count": 1})

    # 按 count 排序，保留前 10 个
    targets.sort(key=lambda x: x.get("count", 0), reverse=True)
    profile.favorite_targets = targets[:10]

    await session.commit()
    await session.refresh(profile)
    return profile


# ============================================================
#  RevengeRelation CRUD (复仇关系)
# ============================================================

async def record_revenge_relation(
    session: AsyncSession,
    attacker_handle: str,
    victim_handle: str,
) -> RevengeRelation:
    """记录复仇关系（attacker 喷了 victim）"""
    result = await session.execute(
        select(RevengeRelation).where(
            RevengeRelation.attacker_handle == attacker_handle.lower(),
            RevengeRelation.victim_handle == victim_handle.lower(),
        )
    )
    relation = result.scalar_one_or_none()

    if relation:
        relation.attack_count += 1
        relation.last_attack_at = datetime.utcnow()
    else:
        relation = RevengeRelation(
            attacker_handle=attacker_handle.lower(),
            victim_handle=victim_handle.lower(),
        )
        session.add(relation)

    await session.commit()
    await session.refresh(relation)
    return relation


async def get_revenge_context(
    session: AsyncSession,
    target_handle: str,
    requester_handle: str,
) -> Optional[dict]:
    """检查 target 是否曾经喷过 requester（复仇模式）"""
    result = await session.execute(
        select(RevengeRelation).where(
            RevengeRelation.attacker_handle == target_handle.lower(),
            RevengeRelation.victim_handle == requester_handle.lower(),
        )
    )
    relation = result.scalar_one_or_none()

    if relation:
        return {
            "revenge_mode": True,
            "attack_count": relation.attack_count,
            "last_attack_at": relation.last_attack_at.isoformat() if relation.last_attack_at else None,
        }
    return None


# ============================================================
#  Global Stats
# ============================================================

async def get_global_stats(session: AsyncSession) -> dict:
    """获取全局统计数据"""
    # 总喷人次数
    total_roasts_result = await session.execute(
        select(func.count(ProcessedMention.id)).where(
            ProcessedMention.trigger_type == TriggerType.X_ROAST,
            ProcessedMention.status == ProcessingStatus.COMPLETED,
        )
    )
    total_roasts = total_roasts_result.scalar() or 0

    # 被喷用户数
    total_targets_result = await session.execute(select(func.count(RoastProfile.id)))
    total_targets = total_targets_result.scalar() or 0

    # 请求者数
    total_requesters_result = await session.execute(select(func.count(RequesterProfile.id)))
    total_requesters = total_requesters_result.scalar() or 0

    # 被喷最多的人
    top_victim_result = await session.execute(
        select(RoastProfile).order_by(desc(RoastProfile.roast_count)).limit(1)
    )
    top_victim = top_victim_result.scalar_one_or_none()

    # 喷人最多的人
    top_roaster_result = await session.execute(
        select(RequesterProfile).order_by(desc(RequesterProfile.request_count)).limit(1)
    )
    top_roaster = top_roaster_result.scalar_one_or_none()

    return {
        "total_roasts": total_roasts,
        "total_targets": total_targets,
        "total_requesters": total_requesters,
        "top_victim": {
            "handle": top_victim.target_handle,
            "count": top_victim.roast_count,
        } if top_victim else None,
        "top_roaster": {
            "handle": top_roaster.username,
            "count": top_roaster.request_count,
        } if top_roaster else None,
    }


# ============================================================
#  Auth CRUD (登录用户相关)
# ============================================================

async def get_requester_profile_by_id(
    session: AsyncSession,
    user_id: str,
) -> Optional[RequesterProfile]:
    """根据 user_id 获取请求者画像"""
    result = await session.execute(
        select(RequesterProfile).where(RequesterProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_roasts_by_requester(
    session: AsyncSession,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[ProcessedMention], int]:
    """获取某用户的喷人历史"""
    # 总数
    count_result = await session.execute(
        select(func.count(ProcessedMention.id)).where(
            ProcessedMention.author_id == user_id,
            ProcessedMention.trigger_type == TriggerType.X_ROAST,
            ProcessedMention.status == ProcessingStatus.COMPLETED,
        )
    )
    total = count_result.scalar() or 0

    # 分页数据
    result = await session.execute(
        select(ProcessedMention)
        .where(
            ProcessedMention.author_id == user_id,
            ProcessedMention.trigger_type == TriggerType.X_ROAST,
            ProcessedMention.status == ProcessingStatus.COMPLETED,
        )
        .order_by(desc(ProcessedMention.created_at))
        .offset(offset)
        .limit(limit)
    )
    roasts = result.scalars().all()

    return list(roasts), total
