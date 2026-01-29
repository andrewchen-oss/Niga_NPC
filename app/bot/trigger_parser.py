"""
[INPUT]: 依赖 app.db.models 的 TriggerType 枚举
[OUTPUT]: 对外提供 ParseResult 数据类、TriggerParser 解析器
[POS]: bot 模块的触发词解析核心，被 processor.py 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import re
from dataclasses import dataclass
from typing import Optional

from app.db.models import TriggerType


@dataclass
class ParseResult:
    trigger_type: TriggerType
    target_handle: Optional[str] = None
    raw_text: str = ""


class TriggerParser:
    """触发词解析器"""

    # ---- Face Search 触发词 ----
    FACE_SEARCH_TRIGGERS = [
        r"查一下",
        r"这是谁",
        r"这谁",
        r"人脸搜索",
        r"找人",
        r"搜一下",
        r"帮我查",
        r"查查",
        r"face\s*search",
        r"who\s*is\s*this",
        r"find\s*this",
        r"search\s*face",
    ]

    # ---- X Roast 触发词 ----
    X_ROAST_TRIGGERS = [
        # 点评系列
        r"点评一下",
        r"点评",
        r"评价一下",
        r"评价",
        r"锐评一下",
        r"锐评",
        # 吐槽系列
        r"吐槽一下",
        r"吐槽",
        # 喷系列
        r"喷一下",
        r"喷他",
        r"喷她",
        r"喷它",
        r"开喷",
        r"去喷",
        r"帮喷",
        r"给我喷",
        # 骂系列
        r"骂一下",
        r"骂他",
        r"骂她",
        r"开骂",
        # 英文
        r"roast",
        r"critique",
        r"roast\s*him",
        r"roast\s*her",
    ]

    def __init__(self, bot_username: str):
        self.bot_username = bot_username.lower().strip("@")

        self.face_search_pattern = re.compile(
            "|".join(self.FACE_SEARCH_TRIGGERS), re.IGNORECASE
        )
        self.x_roast_pattern = re.compile(
            "|".join(self.X_ROAST_TRIGGERS), re.IGNORECASE
        )
        self.mention_pattern = re.compile(r"@(\w+)", re.IGNORECASE)

    def parse(self, text: str) -> ParseResult:
        # 移除对 bot 自己的 @
        cleaned_text = re.sub(
            rf"@{self.bot_username}\b",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        # ---- 检查 Face Search ----
        if self.face_search_pattern.search(cleaned_text):
            return ParseResult(
                trigger_type=TriggerType.FACE_SEARCH,
                raw_text=cleaned_text,
            )

        # ---- 检查 X Roast ----
        if self.x_roast_pattern.search(cleaned_text):
            mentions = self.mention_pattern.findall(cleaned_text)
            mentions = [m for m in mentions if m.lower() != self.bot_username]
            target_handle = mentions[0] if mentions else None

            return ParseResult(
                trigger_type=TriggerType.X_ROAST,
                target_handle=target_handle,
                raw_text=cleaned_text,
            )

        return ParseResult(
            trigger_type=TriggerType.UNKNOWN,
            raw_text=cleaned_text,
        )
