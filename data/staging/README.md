# Collector snapshot contract

每天的采集器只负责向本目录写入平台快照。发布脚本负责后续全部工作：汽车内容过滤、去重、热度排序、每平台取 30 条、失败回退、封面缓存与原子发布。

文件名使用 `douyin.json`、`xiaohongshu.json`、`weibo.json`。结构如下：

```json
{
  "platform": "抖音",
  "collectedAt": "2026-09-23T09:00:00+08:00",
  "status": "ok",
  "window": "近7天",
  "items": [
    {
      "externalId": "作品ID",
      "title": "具体车型或具体事件标题",
      "author": "作者",
      "dateLabel": "3小时前",
      "likes": 12000,
      "engagement": "1.2万赞",
      "contentFormat": "视频封面",
      "cover": "https://...",
      "source": "https://..."
    }
  ]
}
```

当某个平台没有新快照、快照损坏或被拦截时，`refresh_pipeline.py` 会继续使用该平台上一次成功发布的数据。不会因为单个平台失败清空整个网站。
