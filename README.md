# 车势 Radar

汽车热点与三平台 Top Case 工作台。网站读取 `dist/data/hotspots.json`，所有页面内容可静态部署到腾讯云。

## 固定更新流程

1. 当日热点写入 `data/staging/events.json`，三个平台批量采集器写入 `data/staging/*.json`。
2. 每天运行一次 `./scripts/run_daily.sh`，统一刷新热点与 Top Case。
3. 脚本自动完成汽车过滤、去重、平台配额、失败回退、封面本地缓存和原子发布。

采集器只输出少量标准字段，后续逻辑由统一脚本处理。抖音当前采用“近一周 + 点赞排序 + 当天车型词补充”，整页读取列表卡片，不逐条打开作品。小红书需要按详情页可见互动核验，发布层仍使用相同快照格式。

## 腾讯云定时任务

服务器设置为 `Asia/Shanghai` 后，把 `deploy/cron.example` 中的目录替换为实际部署目录并加入 crontab。当日热点与 Top Case 每天更新一次；任一数据源失败时，网站继续展示上一版数据。

本地预览：

```bash
cd dist
python3 -m http.server 4173
```
