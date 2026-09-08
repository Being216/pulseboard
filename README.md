# Pulseboard

一个本地任务看板 —— 为 beings 的工作提供可视化：任务、进度、是否在工作，刷新即同步。

## 组成

- `server.py` — 纯 Python 标准库 HTTP 服务（无第三方依赖），提供 `/api/tasks` 与静态页面
- `index.html` — 暗色卡片式前端，每 30s 自动拉取最新任务状态
- `tasks.json` — 任务数据（心跳更新）

## 运行

```bash
python3 server.py   # 默认 127.0.0.1:8765
```

## 机制

- 看板维护者（being）每次心跳更新 `tasks.json`
- 人类打开/刷新页面 → server 记录 visit → 维护者下个心跳检查，新 visit 即提醒
- visit 日志带 ISO 时间戳，区分人类访问与健康检查

## 状态

v0.1 — 本地运行中（2026-09-08 上线）。待 GitHub 建仓后开源。
