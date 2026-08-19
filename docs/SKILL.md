---
name: obsidian-home-dashboard
description: "Use when setting up an Obsidian homepage dashboard."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags: [Obsidian, Homepage, Dashboard, Dataview, Install]
    related_skills: [obsidian-customization, obsidian]
---

# Obsidian 主页仪表盘（Home Dashboard）安装

把任意 Obsidian 库变成带写作统计的主页仪表盘：每日字数进度环、本周柱状图、库统计、长文进度、可点击便签、学习时间、可拖拽排序卡片、最近打开列表。

## When to Use（触发条件）

- 用户想把某个 Obsidian 库搭成主页仪表盘（或把已有主页复制/部署到新库）
- 用户看到别人（如 estella333）的 Obsidian 主页想一键复刻
- 与 `obsidian-customization` skill 的关系：本 skill 是该主页的**完整安装包**（模板+样式+脚本+步骤）；obsidian-customization 提供通用 Obsidian 配置能力（vault 定位、URI 按钮、dataview 语法等），两者可搭配使用。

## 前置依赖

- Obsidian 客户端（任意平台）
- 目标 vault 路径（找不到时脚本自动读 `obsidian.json`）
- bash + python3 + curl（一键脚本路径）
- Dataview 插件 ≥0.5.70（脚本自动下载）、Homepage 插件（脚本自动下载）

## 快速开始（推荐：一键脚本）

skill 自带 `scripts/install_homepage.sh`，把 `scripts/` 与 `templates/` 目录复制到目标机器任意位置后：

```bash
bash install_homepage.sh                          # 自动定位 vault（多库优先当前打开的）
bash install_homepage.sh -v "/path/to/vault"      # 指定库
bash install_homepage.sh -i "00_Inbox" -a "附件"  # 自定义收件箱/附件目录名
bash install_homepage.sh --no-plugins             # 不自动下载插件（离线环境）
bash install_homepage.sh --with-study-time        # 额外安装学习时间统计（macOS）
```

脚本自动完成（**全部幂等**，可重复运行）：

1. 定位 vault：`-v` 参数 > `obsidian.json`（`open:true` 优先）
2. 备份已有 `Home.md` → `Home.md.bak-<时间戳>`
3. 渲染模板：`{{VAULT_ENCODED}}`（vault 名 URL 编码）、`{{INBOX_FOLDER}}`、`{{ATTACH_FOLDER}}`（读 app.json `attachmentFolderPath`，默认「附件」）
4. 复制并启用 CSS：`.obsidian/snippets/` 下 `homepage.css`、`fix-flicker.css`，用 python 合并 `appearance.json` 的 `enabledCssSnippets`（保留现有项）
5. 检查/下载插件：从 `github.com/<repo>/releases/latest/download/{main.js,manifest.json,styles.css}` 下载 dataview（blacksmithgu/obsidian-dataview）与 homepage（mirnovov/obsidian-homepage），合并进 `community-plugins.json`
6. （可选）学习时间：脚本装到 `~/StudyTimeWatcher/`，写 `config.json`（vault+附件目录），注册 LaunchAgent `com.obsidian-home-dashboard.studytime` 常驻

完成后**重启 Obsidian**（`Cmd/Ctrl+P` → Reload app without saving），在 Homepage 插件设置里把首页设为 `Home`。

## 手动搭建（无 bash/离线/agent 逐步执行）

### 1. 定位 vault

`OBSIDIAN_VAULT_PATH` 未设置时读：
- macOS: `~/Library/Application Support/obsidian/obsidian.json`
- Windows: `%APPDATA%\obsidian\obsidian.json`
- Linux: `~/.config/obsidian/obsidian.json`

取 `vaults` 中 `open:true` 的 `path`（单库即唯一条目）。

### 2. 渲染 Home.md

用 `templates/Home.md` 模板，python 替换三个占位符后写入 `<vault>/Home.md`：

```python
import urllib.parse, os
enc = urllib.parse.quote(os.path.basename(vault))   # 中文库名 → %E6%9C%B5...
tpl = tpl.replace("{{VAULT_ENCODED}}", enc).replace("{{INBOX_FOLDER}}", inbox).replace("{{ATTACH_FOLDER}}", attach)
```

### 3. 安装 CSS

复制 `templates/homepage.css`、`templates/fix-flicker.css` 到 `<vault>/.obsidian/snippets/`，然后 read-modify-write 合并 `appearance.json` 的 `enabledCssSnippets`（**保留现有键与已有片段**）。

### 4. 插件（二选一）

- 手动：插件设置 → 社区插件 → 浏览 → 安装 Dataview、Homepage
- 脚本化：下载 release 三个资产到 `.obsidian/plugins/<id>/`，再把 id 追加进 `community-plugins.json`

### 5. 配置 Homepage 插件

`.obsidian/plugins/homepage/data.json`：

```json
{"homepages": {"<任意名>": {"value": "Home", "openOnStartup": true, "openWhenEmpty": true, "view": "Live Preview"}}}
```

`autoCreate` 保持 false 即可（Home.md 已由模板生成）；Live Preview 才让便签/按钮可交互。

### 6. 验证

见下方「验证清单」。

## 自定义指南

- **每日字数目标**：Home.md 头部属性 `goal: 3500`
- **长文进度**：`thesis_folder`（统计文件夹）、`thesis_goal`（目标字数）；不需要就删掉这两行属性 + 正文「🎓 长文进度」代码段
- **收件箱统计**：改模板/脚本的 `{{INBOX_FOLDER}}`（默认 `00_Inbox`）
- **最近打开图标**：改 Home.md 末尾 `icons` 映射，追加常用文件夹 emoji
- **卡片顺序**：拖动即改，`localStorage` 按 vault 名隔离记忆
- **学习时间统计的 App**：改 `study_time_watch.py` 顶部 `TARGETS`（bundle id → 显示名）

## 验证清单

1. 重启后主页渲染出：问候语、按钮、6 张卡（进度环/柱状图/数字/便签/学习时间）、最近打开列表
2. 点「⚡ 快速记笔记」「📅 今日日记」在新标签打开（说明 vault 名编码正确）
3. 便签输入文字，800ms 后自动保存到 `<附件>/home-memo.txt`
4. 拖动卡片换位，刷新页面顺序保持
5. 今日写作卡数字 ≈ 全库当天修改 md 字数（Home.md 自身不计）
6. （启用学习时间后）卡上显示今日时长；`附件/study-time.json` 每 10 分钟刷新

## 坑（Pitfalls）

1. **中文/非 ASCII vault 名必须 URL 编码**，否则 `obsidian://` 按钮静默失败（`urllib.parse.quote`）
2. **Dataview 0.5.70+ 移除了 `file.content`**：统计字数用 `await dv.io.load(p.file.path)`；`dv.date()` 不接受数字时间戳（用 `dv.luxon.DateTime.fromMillis()`）
3. **bash heredoc 里的 python 没有 `__file__`**：模板路径要作为参数传入，不能 `os.path.dirname(__file__)`
4. **bash 变量后紧跟全角括号会炸**：`$MISSING（...）` 中全角 `（` 被当作变量名一部分（UTF-8 locale），必须写 `${MISSING}`
5. **JSON 配置必须 read-modify-write**：合并而非覆盖 `appearance.json` / `community-plugins.json`，保留用户已有设置
6. **插件下载被网络拦**（代理 fake-ip / 防火墙）：`curl -fsSL --retry 3` 重试；仍失败则提示用户手动安装，勿让脚本整体失败（`--no-plugins` 可跳过）
7. **Homepage 插件 `autoCreate:false` 且 Home.md 不存在** → 启动静默不显示首页；模板已保证 Home.md 存在
8. **附件目录名来自 app.json**：`attachmentFolderPath` 非默认「附件」时，便签路径与学习时间 JSON 路径必须同步替换，否则读不到/写不进
9. **CSS 依赖主题变量**（`--background-secondary` 等）：配 Minimal 等主题效果最佳；默认主题也能用
10. **脚本幂等**：重复运行会生成 `.bak-<时间戳>` 备份、不会重复追加 snippet/插件 id

## 附属文件

- `templates/Home.md` — 主页模板（`{{VAULT_ENCODED}}` / `{{INBOX_FOLDER}}` / `{{ATTACH_FOLDER}}` 占位符）
- `templates/homepage.css` — 卡片/环/柱状图/按钮/便签样式
- `templates/fix-flicker.css` — 侧边栏/日历闪烁修复（可选）
- `scripts/install_homepage.sh` — 一键安装脚本（bash + python3 + curl，幂等）
- `scripts/study_time_watch.py` — 学习时间守护进程（macOS lsappinfo，每 10s 轮询）
