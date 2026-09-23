# 车势 Radar

汽车热点与三平台 Top Case 工作台。网站读取 `dist/data/hotspots.json`，当前由 GitHub 自动更新并通过 Cloudflare Workers 发布。

## 每日自动更新

1. GitHub Actions 每天北京时间 09:00 执行 `.github/workflows/daily-refresh.yml`。
2. `collect_news.py` 从多个公开新闻源采集，只保留汽车内容；先取 24 小时，目标 60 条以上，不足时回溯到 72 小时。
3. 云端分别尝试微博、小红书、抖音。没有登录态或被平台拦截时，只回退该平台，绝不清空其他平台和上一版 Case。
4. 更新后的 JSON 自动提交到 `main`，Cloudflare 随 GitHub 提交自动部署。

手动试跑云端流程：

```bash
./scripts/run_daily.sh
```

## Mac 登录态补采

云端无法稳定携带三平台登录态，所以 Mac 复用日常 Google Chrome 的现有登录状态，在当前窗口临时打开采集标签页并在完成后关闭。它不会自动唤醒电脑；Mac 在 09:15 睡眠时，任务会在唤醒后补跑。补采成功后脚本提交并推送数据，Cloudflare 自动发布。

首次设置：

```bash
./scripts/setup_social_login.sh  # 按提示开启 Chrome 的 Apple Events JavaScript
./scripts/install_local_backfill.sh
```

脚本只读取搜索结果页公开 DOM，不读取或导出 Cookie。运行锁和日志都在 `.local/`，该目录已从 Git 排除。日常手动补采可运行：

```bash
./scripts/run_local_backfill.sh
```

采集器只输出少量标准字段，发布脚本负责汽车过滤、去重、每平台 30 条、失败回退、封面本地缓存和原子发布。

本地预览：

```bash
cd dist
python3 -m http.server 4173
```
