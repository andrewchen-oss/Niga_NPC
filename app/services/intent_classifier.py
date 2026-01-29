"""
[INPUT]: 依赖 openai, app.config, app.db.models
[OUTPUT]: 对外提供 IntentClassifier (classify 方法)
[POS]: services 模块的意图分类器，用 GPT-4o-mini 识别用户意图
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import re
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI

from app.config import get_settings
from app.db.models import TriggerType
from app.utils.logger import logger


@dataclass
class IntentResult:
    trigger_type: TriggerType
    target_handle: Optional[str] = None
    confidence: float = 0.0


SYSTEM_PROMPT = """你是一个 Twitter Bot 的意图分类器。用户 @ 了这个 Bot，你需要判断用户想让 Bot 做什么。

## 两种有效意图：

1. **FACE_SEARCH** - 用户想识别图片中的人脸是谁
   - 必须同时满足以下所有条件：
     a) 消息附带了图片
     b) 用户明确表达想知道图片中人物的身份
     c) 使用了明确的人脸识别/查人关键词：这是谁、这人是谁、who is this、查这人、搜脸、认脸、找人、identify
   - 不是 FACE_SEARCH 的情况：
     * 只发图片没有查人意图
     * 模糊表达如"查一下"、"看看"（不明确是查人）
     * 让 Bot 评价图片中的人（这是 X_ROAST）

2. **X_ROAST** - 用户想让 Bot 去评价/吐槽/攻击某个人
   - 核心判断：用户是否在指挥 Bot 对某人进行评价或攻击
   - 常见表达：喷他、骂他、点评、锐评、roast、开干、冲、搞他、说说这人...
   - 只要用户意图是"让 Bot 对某人做点什么"，就是 X_ROAST

## 关键区分：

X_ROAST：用户在指挥 Bot 行动（"喷他"、"来 开干"、"点评一下"）
UNKNOWN：用户自己在发泄情绪，没有给 Bot 下指令（"你他妈的"、"草"、"傻逼"）

简单说：有动作指向 → X_ROAST，纯情绪发泄 → UNKNOWN

## 输出格式（严格 JSON）：
{"intent": "FACE_SEARCH", "confidence": 0.95}
{"intent": "X_ROAST", "confidence": 0.90}
{"intent": "UNKNOWN", "confidence": 0.80}"""


class IntentClassifier:
    """GPT-4o-mini 意图分类器"""

    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.bot_username = settings.twitter_bot_username.lower()

    async def classify(self, text: str, has_image: bool = False) -> IntentResult:
        """分类用户意图"""
        # ---- 清理文本（移除 bot @） ----
        cleaned_text = re.sub(
            rf"@{self.bot_username}\b", "", text, flags=re.IGNORECASE
        ).strip()

        # ---- 构建上下文 ----
        context = f"用户消息: {cleaned_text}"
        if has_image:
            context += "\n[用户消息附带了图片]"

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": context},
                ],
                temperature=0.1,
                max_tokens=100,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content
            logger.debug(f"Intent classification result: {result_text}")

            # ---- 解析 JSON ----
            import json
            data = json.loads(result_text)

            intent = data.get("intent", "UNKNOWN").upper()
            confidence = float(data.get("confidence", 0.5))

            # ---- 映射到 TriggerType ----
            if intent == "FACE_SEARCH":
                return IntentResult(
                    trigger_type=TriggerType.FACE_SEARCH,
                    confidence=confidence,
                )
            elif intent == "X_ROAST":
                return IntentResult(
                    trigger_type=TriggerType.X_ROAST,
                    confidence=confidence,
                )
            else:
                return IntentResult(
                    trigger_type=TriggerType.UNKNOWN,
                    confidence=confidence,
                )

        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return IntentResult(
                trigger_type=TriggerType.UNKNOWN,
                confidence=0.0,
            )
