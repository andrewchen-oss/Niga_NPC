# db/

> L2 | 父级: /CLAUDE.md

## 成员清单

- `base.py`: SQLAlchemy DeclarativeBase 声明，所有 ORM 模型的基类
- `models.py`: ORM 模型定义 (ProcessedMention, BotState, ActiveRoastRecord)，枚举 (ProcessingStatus, TriggerType)
- `session.py`: AsyncEngine + AsyncSession 工厂，init_db 建表，get_async_session 上下文管理
- `crud.py`: CRUD 操作层 (mention 去重/创建/更新状态、active_roast 记录)

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
