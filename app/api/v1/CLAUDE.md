# api/v1/

> L2 | 父级: /app/api/CLAUDE.md

## 成员清单

- `__init__.py`: v1 路由聚合层，汇总 public 子路由
- `public.py`: 公开 API - 排行榜、档案、统计（无需认证）

## API Endpoints

```
# Public
GET  /api/v1/leaderboard          - 被喷排行榜
GET  /api/v1/profiles/{handle}    - 用户档案
GET  /api/v1/stats                - 全局统计

# Auth
GET  /api/v1/auth/twitter         - 发起 OAuth 登录
GET  /api/v1/auth/callback        - OAuth 回调
GET  /api/v1/auth/me              - 当前用户信息
GET  /api/v1/auth/me/roasts       - 我的喷人历史
POST /api/v1/auth/roast           - 发起喷人（预览模式）
POST /api/v1/auth/logout          - 登出
```

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
