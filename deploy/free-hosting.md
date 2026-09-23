# 免费部署流程

当前阶段先发布 `dist/` 中已经验证过的网站。GitHub Actions 会在每次上传时检查数据文件，Cloudflare Pages 会在检查通过后发布网站。

## GitHub 仓库

1. 新建一个 Private repository，推荐名称 `car-radar`。
2. 不要初始化 README、`.gitignore` 或 License。
3. 在本地项目目录添加远程仓库并推送 `main` 分支。

## Cloudflare Pages

1. 在 Workers & Pages 中创建 Pages 项目。
2. 连接 GitHub 并选择 `car-radar`。
3. Framework preset 选择 None。
4. Build command 留空，Build output directory 填 `dist`。
5. 部署完成后使用 Cloudflare 分配的 `*.pages.dev` 地址访问。

## 自动更新边界

`site-check.yml` 只验证和发布现有数据，不负责抓取平台内容。正式启用每日定时任务前，需要先完成新闻、微博、小红书和抖音采集器，并通过一次云端手动运行验证。
