# handlers/

> L2 | 父级: bot/CLAUDE.md

## 成员清单

- `base.py`: Handler 抽象基类，定义 twitter + api_client 注入和 handle 接口
- `face_search.py`: 人脸搜索处理器，下载图片 → base64 → 调用上游 API → 构建回复
- `x_roast.py`: 用户吐槽处理器，调用上游 API → 本地后处理增强（复仇模式/老朋友模式）→ 返回 roast 内容

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
