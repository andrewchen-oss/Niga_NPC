"""
[INPUT]: 依赖 app.db.base 的 Base
[OUTPUT]: 对外提供 ProcessedMention, BotState, ActiveRoastRecord, RoastProfile, RequesterProfile, RevengeRelation 模型, ProcessingStatus, TriggerType 枚举
[POS]: db 模块的 ORM 模型定义，被 crud.py 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum, Index, Integer, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.db.base import Base


# ============================================================
#  枚举类型
# ============================================================

class ProcessingStatus(enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TriggerType(enum.Enum):
    FACE_SEARCH = "face_search"
    X_ROAST = "x_roast"
    UNKNOWN = "unknown"


# ============================================================
#  已处理的 mention 记录
# ============================================================

class ProcessedMention(Base):
    __tablename__ = "processed_mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ---- Twitter 推文信息 ----
    tweet_id = Column(String(64), unique=True, nullable=False)
    author_id = Column(String(64), nullable=False)
    author_username = Column(String(64), nullable=False)
    tweet_text = Column(Text, nullable=False)
    reply_to_tweet_id = Column(String(64), nullable=True)  # 所属 thread 的原推 ID

    # ---- 处理信息 ----
    trigger_type = Column(SQLEnum(TriggerType), nullable=False)
    target_handle = Column(String(64), nullable=True)  # X_ROAST 的目标用户
    status = Column(SQLEnum(ProcessingStatus), default=ProcessingStatus.PENDING)

    # ---- 回复信息 ----
    reply_tweet_id = Column(String(64), nullable=True)
    reply_text = Column(Text, nullable=True)

    # ---- 错误信息 ----
    error_message = Column(Text, nullable=True)

    # ---- 时间戳 ----
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_processed_mentions_tweet_id", "tweet_id"),
        Index("ix_processed_mentions_status", "status"),
        Index("ix_processed_mentions_created_at", "created_at"),
        Index("ix_processed_mentions_thread_target", "reply_to_tweet_id", "target_handle"),
        Index("ix_processed_mentions_thread_requester", "reply_to_tweet_id", "author_id"),
    )


# ============================================================
#  Bot 状态存储 (key-value)
# ============================================================

class BotState(Base):
    __tablename__ = "bot_state"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(64), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


# ============================================================
#  主动 Roast 记录 (Active Roast)
# ============================================================

class ActiveRoastRecord(Base):
    """记录主动出击喷过的推文，避免重复"""
    __tablename__ = "active_roast_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ---- 目标推文信息 ----
    tweet_id = Column(String(64), unique=True, nullable=False)
    author_id = Column(String(64), nullable=False)
    author_username = Column(String(64), nullable=False)

    # ---- Roast 内容 ----
    roast_content = Column(Text, nullable=False)
    reply_tweet_id = Column(String(64), nullable=True)

    # ---- 时间戳 ----
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_active_roast_tweet_id", "tweet_id"),
        Index("ix_active_roast_author_id", "author_id"),
    )


# ============================================================
#  被喷者档案 (Long-Term Memory)
# ============================================================

class RoastProfile(Base):
    """被喷用户的档案，记录被喷历史和统计"""
    __tablename__ = "roast_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ---- X 用户标识 ----
    target_handle = Column(String(64), unique=True, nullable=False, index=True)
    target_user_id = Column(String(64), nullable=True)

    # ---- 统计数据 ----
    roast_count = Column(Integer, default=0, nullable=False)
    unique_roasters = Column(Integer, default=0, nullable=False)
    first_roasted_at = Column(DateTime(timezone=True), nullable=True)
    last_roasted_at = Column(DateTime(timezone=True), nullable=True)

    # ---- 档案数据 ----
    roast_themes = Column(JSONB, default=list)  # ["技术菜", "审美差"]

    # ---- 时间戳 ----
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_roast_profiles_roast_count", "roast_count"),
        Index("ix_roast_profiles_last_roasted", "last_roasted_at"),
    )


# ============================================================
#  请求者画像 (Long-Term Memory)
# ============================================================

class RequesterProfile(Base):
    """请求喷人的用户画像"""
    __tablename__ = "requester_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ---- X 用户标识 ----
    user_id = Column(String(64), unique=True, nullable=False, index=True)
    username = Column(String(64), nullable=False)

    # ---- 统计数据 ----
    request_count = Column(Integer, default=0, nullable=False)
    favorite_targets = Column(JSONB, default=list)  # [{"handle": "xx", "count": 5}]

    # ---- 前端登录相关 ----
    is_registered = Column(Boolean, default=False)
    oauth_access_token = Column(Text, nullable=True)
    oauth_refresh_token = Column(Text, nullable=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # ---- 时间戳 ----
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_requester_profiles_request_count", "request_count"),
    )


# ============================================================
#  复仇关系 (Long-Term Memory)
# ============================================================

class RevengeRelation(Base):
    """记录谁喷过谁，用于复仇模式"""
    __tablename__ = "revenge_relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # ---- 关系 ----
    attacker_handle = Column(String(64), nullable=False)  # 曾经的攻击者
    victim_handle = Column(String(64), nullable=False)    # 曾经的受害者

    # ---- 统计 ----
    attack_count = Column(Integer, default=1, nullable=False)
    last_attack_at = Column(DateTime(timezone=True), server_default=func.now())

    # ---- 时间戳 ----
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("attacker_handle", "victim_handle", name="uq_revenge_attacker_victim"),
        Index("ix_revenge_attacker", "attacker_handle"),
        Index("ix_revenge_victim", "victim_handle"),
    )
