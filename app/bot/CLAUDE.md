# bot/

> L2 | 父级: /CLAUDE.md

## 成员清单

- `stream.py`: Filtered Stream v2 监听器，规则管理 + 长连接 + 自动重连 + 并发处理分发
- `active_roast.py`: 主动出击调度器，定时刷 Home Timeline 随机开喷 (10分钟一条)
- `event_parser.py`: v2 流式数据解析器，将 Filtered Stream 推文转换为标准 mention 字典
- `processor.py`: 单条 mention 处理核心，含幂等去重 + 触发词解析 + Handler 分发 + 回复发送
- `trigger_parser.py`: 触发词解析器，正则匹配中英文触发词，提取目标 handle
- `response_builder.py`: 回复内容生成器，抽象风格随机选词
- `handlers/`: 功能处理器子模块

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
