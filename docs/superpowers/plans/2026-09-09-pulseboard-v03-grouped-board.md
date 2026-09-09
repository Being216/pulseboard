# Pulseboard v0.3 Grouped Collapsible Board Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有平铺任务看板升级为按状态分组、可折叠且可记忆展开状态的四组看板，同时保持 v0.2 的任务详情、操作按钮和 API 兼容。

**Architecture:** 保持 `server.py` 和 `/api/tasks` 数据结构不变；在 `index.html` 内增加纯函数式的状态归组/排序逻辑，以及使用 `localStorage` 的分组展开状态。原有任务卡片和 `#grid` 事件代理继续复用，只把任务容器变成四个 section。

**Tech Stack:** Python 3 标准库 HTTP server、原生 HTML/CSS/JavaScript、Node.js 语法检查、Python unittest/源码回归检查。

---

### Task 1: 建立 v0.3 回归检查并确认当前代码会失败

**Files:**
- Create: `tests/test_v03_grouped_board.py`
- Test: `index.html`, `server.py`, `tasks.json`

- [x] **Step 1: Write the failing tests**

  检查实际状态枚举仍为 `pending / in_progress / blocked / done`，并检查页面尚未具备四组 section、折叠状态存储及排序入口；测试要在旧版页面上因缺少新行为而失败。

- [x] **Step 2: Run the focused test to verify it fails**

  Run: `python3 -m unittest tests/test_v03_grouped_board.py -v`

  Expected: FAIL，失败原因是 `index.html` 缺少 v0.3 分组/折叠实现。

### Task 2: 实现前端状态分组、排序和折叠持久化

**Files:**
- Modify: `index.html`（CSS、分组配置、归组/排序/折叠状态 helper、渲染入口、事件代理）

- [x] **Step 1: Add the minimal CSS and semantic section structure**

  增加 `.task-group`、`.group-header`、`.group-list`、`.group-empty` 样式；组头使用 button，设置 `aria-expanded` 和 `aria-controls`，保持已有 `.grid`/`.card` 样式不变。

- [x] **Step 2: Add pure grouping and sorting helpers**

  使用四个固定组：`in_progress`、`todo`、`blocked`、`done`；`todo` 接受 `todo/pending`，`done` 接受 `done/completed`。进行中读取 `updated_at/updatedAt` 降序，已完成优先读取 `completed_at/completedAt/finished_at/finishedAt/done_at/doneAt`，再回退到 `updated_at/updatedAt`；字段缺失时保持稳定原序。

- [x] **Step 3: Add localStorage-backed default state**

  使用版本化键 `pulseboard.groupState.v03`，默认 `{in_progress: true, todo: true, blocked: false, done: false}`；读取失败、内容非法或浏览器禁用存储时回退默认值，切换后尽力保存且不影响任务操作。

- [x] **Step 4: Replace the flat task render with four collapsible sections**

  每组始终渲染，组头显示中文组名和任务数；空组渲染空状态提示；非空组复用 `renderTask`，不移除编辑/取消/刷新/提醒按钮。

- [x] **Step 5: Update click handling and reload rendering**

  在现有 `#grid` 事件代理中增加组头切换分支，保留任务操作分支；`load()` 改为调用分组渲染函数，轮询/编辑/取消后的刷新继续恢复已保存折叠状态。

### Task 3: 更新 v0.3 文档并完成验证

**Files:**
- Create: `docs/v0.3-CHANGELOG.md`
- Verify: `index.html`, `server.py`, `tests/test_v03_grouped_board.py`

- [x] **Step 1: Run the focused regression test**

  Run: `python3 -m unittest tests/test_v03_grouped_board.py -v`

  Expected: PASS，覆盖四组、默认折叠配置、持久化键、排序字段兼容和保留操作入口。

- [x] **Step 2: Run required syntax checks**

  Run: `python3 -m py_compile server.py` and `sed -n '/<script>/,/<\/script>/p' index.html | sed '1d;$d' | node --check /dev/stdin`

  直接将 `index.html` 的 `<script>` 内容送入 Node 语法检查；若当前环境没有 Node，则改用括号/标签配对检查并明确记录。

- [x] **Step 3: Inspect the final diff and data/API compatibility**

  Run: `git diff --check && git diff -- index.html server.py docs/v0.3-CHANGELOG.md tests/test_v03_grouped_board.py`

  确认只包含本需求相关改动、不触碰 `.git`、`server.py` 的既有操作接口仍存在，并补写简短 CHANGELOG。
