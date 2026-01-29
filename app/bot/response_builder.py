"""
[INPUT]: 无外部依赖，纯逻辑
[OUTPUT]: 对外提供 ResponseBuilder 回复构建器
[POS]: bot 模块的回复内容生成器，被 handlers 和 processor 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import random


class ResponseBuilder:
    """
    构建 Bot 回复
    风格：抽象、玩梗、简短
    """

    # ============================================================
    #  Face Search
    # ============================================================

    NO_IMAGE = [
        "？图呢",
        "图呢 急了",
        "没图你让我查空气？",
        "图没了 你在逗我",
        "发图啊 大哥",
    ]

    NO_FACE = [
        "这图里没人 你玩我呢",
        "没人脸 发的啥",
        "检测不到脸 抽象画？",
        "人呢 人在哪",
        "没脸 换一张",
    ]

    NO_RESULT = [
        "查无此人 干净得可怕",
        "搜不到 隐形人？",
        "啥也没有 石头缝蹦出来的？",
        "没结果 高人啊",
        "一无所获 深藏功与名",
    ]

    SEARCH_SUCCESS_PREFIX = [
        "挖到了：",
        "找到了：",
        "有结果：",
        "搜到了：",
        "看看这些：",
    ]

    # ============================================================
    #  X Roast
    # ============================================================

    NO_TARGET = [
        "？点评谁",
        "你要我喷谁 说啊",
        "@ 一个人出来",
        "没目标 喷空气？",
        "谁 说清楚",
    ]

    USER_NOT_FOUND = [
        "这人不存在 召唤虚空？",
        "查无此人 打错字了吧",
        "没这用户 你编的？",
        "不存在 检查下handle",
        "找不到 蒸发了？",
    ]

    # ============================================================
    #  通用
    # ============================================================

    ERROR = [
        "出错了 等会再试",
        "寄了 稍后再来",
        "系统开小差了",
        "炸了 别急",
        "出问题了 待会试试",
    ]

    # ============================================================
    #  方法
    # ============================================================

    @classmethod
    def no_image(cls) -> str:
        return random.choice(cls.NO_IMAGE)

    @classmethod
    def no_face(cls) -> str:
        return random.choice(cls.NO_FACE)

    @classmethod
    def no_result(cls) -> str:
        return random.choice(cls.NO_RESULT)

    @classmethod
    def face_search_success(cls, links: list[str]) -> str:
        prefix = random.choice(cls.SEARCH_SUCCESS_PREFIX)
        links_text = "\n".join(links[:3])
        return f"{prefix}\n{links_text}"

    @classmethod
    def no_target(cls) -> str:
        return random.choice(cls.NO_TARGET)

    @classmethod
    def user_not_found(cls) -> str:
        return random.choice(cls.USER_NOT_FOUND)

    @classmethod
    def roast_success(cls, roast_text: str, target_handle: str | None = None) -> str:
        """构建喷人回复，前面@被喷的人"""
        if target_handle:
            # 确保handle没有@前缀
            handle = target_handle.lstrip("@")
            return f"@{handle} {roast_text}"
        return roast_text

    @classmethod
    def error(cls) -> str:
        return random.choice(cls.ERROR)
