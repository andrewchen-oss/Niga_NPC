# services/

> L2 | 父级: /CLAUDE.md

## 成员清单

- `twitter.py`: Twitter API 封装 (Tweepy Client)，reply_to_tweet / download_image / get_home_timeline
- `upstream_api.py`: wtf.nuwa.world API 客户端 (httpx)，face_search / x_roast，带重试
- `intent_classifier.py`: GPT-4o-mini 意图分类器，识别 FACE_SEARCH / X_ROAST 意图

[PROTOCOL]: 变更时更新此头部，然后检查 CLAUDE.md
