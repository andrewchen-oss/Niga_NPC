"""
[INPUT]: 依赖 app.config 的 get_settings
[OUTPUT]: 对外提供 logger 实例、setup_logger 初始化函数
[POS]: utils 模块的日志配置，被全局消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

import logging
import sys

from app.config import get_settings

logger = logging.getLogger("skyeye_bot")


def setup_logger():
    settings = get_settings()

    logger.setLevel(settings.log_level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(settings.log_level.upper())

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)
