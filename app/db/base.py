"""
[INPUT]: 依赖 sqlalchemy.orm 的 DeclarativeBase
[OUTPUT]: 对外提供 Base ORM 基类
[POS]: db 模块的 ORM 基类声明，被 models.py 和 session.py 消费
[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
