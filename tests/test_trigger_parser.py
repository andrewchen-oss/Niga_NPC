"""
[INPUT]: 依赖 app.bot.trigger_parser
[OUTPUT]: TriggerParser 的单元测试
[POS]: tests 模块的触发词解析测试
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import pytest
from app.bot.trigger_parser import TriggerParser, TriggerType


@pytest.fixture
def parser():
    return TriggerParser("SkyeyeBot")


class TestFaceSearchTriggers:
    def test_chinese_triggers(self, parser):
        cases = [
            "@SkyeyeBot 查一下这是谁",
            "@SkyeyeBot 这是谁",
            "@SkyeyeBot 帮我查查",
            "这谁啊 @SkyeyeBot",
        ]
        for text in cases:
            result = parser.parse(text)
            assert result.trigger_type == TriggerType.FACE_SEARCH, f"Failed: {text}"

    def test_english_triggers(self, parser):
        cases = [
            "@SkyeyeBot face search",
            "@SkyeyeBot who is this",
            "find this person @SkyeyeBot",
        ]
        for text in cases:
            result = parser.parse(text)
            assert result.trigger_type == TriggerType.FACE_SEARCH, f"Failed: {text}"


class TestXRoastTriggers:
    def test_with_target(self, parser):
        result = parser.parse("@SkyeyeBot 点评一下 @elonmusk")
        assert result.trigger_type == TriggerType.X_ROAST
        assert result.target_handle == "elonmusk"

    def test_without_target(self, parser):
        result = parser.parse("@SkyeyeBot 点评一下")
        assert result.trigger_type == TriggerType.X_ROAST
        assert result.target_handle is None

    def test_english_roast(self, parser):
        result = parser.parse("@SkyeyeBot roast @jack")
        assert result.trigger_type == TriggerType.X_ROAST
        assert result.target_handle == "jack"


class TestUnknownTrigger:
    def test_no_trigger(self, parser):
        result = parser.parse("@SkyeyeBot 你好")
        assert result.trigger_type == TriggerType.UNKNOWN

    def test_random_text(self, parser):
        result = parser.parse("@SkyeyeBot 今天天气不错")
        assert result.trigger_type == TriggerType.UNKNOWN
