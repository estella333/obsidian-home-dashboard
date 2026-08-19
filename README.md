# 🏠 Obsidian 主页仪表盘（Home Dashboard）

一个**开箱即用**的 Obsidian 主页：进度环、周写作柱状图、库统计、长文进度、便签、学习时间、拖拽排序卡片、最近打开——克隆后跑一条命令即可安装到任意 vault。

> 原为个人博士论文写作库（PARA 结构）的主页，现已参数化通用化，适配任何库。

## ✨ 功能

| 卡片 | 说明 |
| --- | --- |
| 📝 今日进度 | **当日真正新增字数** / 目标（快照字符级 diff：改旧文件只算改动量，悬停可见每文件明细；目标在 Home.md 头部 `goal` 修改） |
| 📈 本周写作 | 周一到周日每日字数柱状图（过去天用快照历史，今天实时） |
| 📊 库统计 | 全库笔记数 + 收件箱待整理数 |
| 🎓 长文进度 | 指定文件夹（如论文初稿）累计字数 / 目标 |
| 📝 便签 | 点击直接输入，自动保存到附件文件夹（不污染字数统计） |
| ⏱️ 学习时间 | 今日 Obsidian/Typora/预览 使用时长（可选功能，macOS） |
| 🕘 最近打开 | 最近浏览的 5 篇笔记，自动识别常见目录图标 |

其他特性：

- **卡片拖拽排序**：按住卡片拖动即可换位，顺序持久化到附件文件（重启/换设备保持，localStorage 兜底）
- **实时刷新**：每 30 秒自动重算今日字数并更新卡片（走 Obsidian 缓存，不卡；视图关闭自动停止）
- **悬停明细**：鼠标悬停进度环，显示今日各文件新增字数 Top 12
- **问候语 + 日期**：按时间段自动切换「早上好 / 下午好 / 夜深了…」
- **字数统计引擎**：快照 + 字符级 diff——每天首次渲染建立全库快照，之后只算「今天真正新增的字数」，旧文件改几个字算几个字（不再整篇计入）
- **按钮一键跳转**：⚡ 快速记笔记、📅 今日日记（自动适配你的 vault 名）

## 📦 依赖

- Obsidian（废话 😄）
- [Dataview](https://github.com/blacksmithgu/obsidian-dataview) 插件 —— 安装脚本会自动下载
- [Homepage](https://github.com/mirnovov/obsidian-homepage) 插件 —— 安装脚本会自动下载，用于启动时打开 Home.md

## 🚀 一键安装

```bash
git clone https://github.com/estella333/obsidian-home-dashboard.git
cd obsidian-home-dashboard
bash install.sh
```

脚本会自动：

1. 定位你的 Obsidian 库（读取 Obsidian 配置文件，多库时优先当前打开的库）
2. 备份已有 `Home.md`
3. 生成适配你 vault 名的 `Home.md`（按钮 URI 自动编码）
4. 安装并启用 CSS 片段 `homepage` / `fix-flicker`
5. 自动下载并启用 Dataview、Homepage 插件（网络受限时提示手动安装）

安装完**重启 Obsidian**（`Cmd/Ctrl+P` → *Reload app without saving*），并在 Homepage 插件设置中把首页设为 `Home` 即可。

### 常用参数

```bash
bash install.sh -v "/path/to/your/vault"   # 指定库路径（跳过自动定位）
bash install.sh -i "00_Inbox"              # 收件箱文件夹名（默认 00_Inbox）
bash install.sh -a "附件"                  # 附件文件夹名（默认读 Obsidian 设置）
bash install.sh --no-plugins               # 不自动下载插件
bash install.sh --with-study-time          # 额外安装「学习时间」统计（macOS）
```

## 🤖 使用 Hermes skill 搭建

本仓库同时提供 [Hermes Agent](https://hermes-agent.nousresearch.com) skill 版本（`docs/SKILL.md`，含完整模板/样式/脚本附属文件）。任何 Hermes 用户对 AI 说「用 obsidian-home-dashboard skill 给我的库搭主页」即可自动完成：定位库 → 渲染模板 → 装 CSS → 启用插件 → 验证。

## ⏱️ 学习时间（可选，macOS）

首页的「学习时间」卡需要一个小型后台守护进程统计 Obsidian/Typora/预览 的前台使用时长：

```bash
bash install.sh --with-study-time
```

- 脚本安装到 `~/StudyTimeWatcher/`，数据**双写**：主写应用数据目录（`~/Library/Application Support/StudyTime/study-time.json`，launchd 环境无 TCC 限制），同时尽力同步一份到 vault 的 `附件/study-time.json`（被系统权限拦截时静默跳过）
- Home.md 优先读 frontmatter `study_json_path` 指定的绝对路径，未配置则读附件；vault 在 `~/Desktop` 等受保护目录时建议填上应用数据目录的绝对路径
- macOS 下自动注册 LaunchAgent 常驻（每 10 秒检测一次前台 App，CPU 占用 <0.1%）
- 想统计其他 App：编辑 `study_time_watch.py` 顶部的 `TARGETS` 字典（bundle id → 显示名）
- 卸载：`launchctl unload ~/Library/LaunchAgents/com.obsidian-home-dashboard.studytime.plist`

## 🛠️ 自定义

- **每日字数目标**：编辑 `Home.md` 头部属性 `goal: 3500`
- **学习时间 JSON 路径**：frontmatter `study_json_path` 填绝对路径则优先读它；留空读附件 `study-time.json`
- **长文进度**：`thesis_folder`（统计的文件夹）、`thesis_goal`（目标字数）；不需要就删掉这两行属性，并删掉正文「🎓 长文进度」代码段
- **收件箱**：按钮和统计卡里的文件夹名在安装时已按你的参数生成；手动改名请搜索 Home.md 中的 `00_Inbox`
- **最近打开的图标**：修改 Home.md 末尾 `icons` 映射，增加你常用文件夹的 emoji
- **卡片顺序**：拖动卡片即改，自动记住

## 📂 仓库结构

```
obsidian-home-dashboard/
├── install.sh              # 一键安装脚本（bash + python3）
├── templates/Home.md       # 主页模板（{{占位符}} 由安装脚本替换）
├── snippets/               # CSS 片段（主页美化 + 侧边栏闪烁修复）
├── scripts/study_time_watch.py  # 学习时间守护脚本（可选，macOS）
├── scripts/daily_wordcount.py   # 可选：git 字符粒度字数工具（快照方案的备选/对账）
└── docs/SKILL.md           # Hermes skill 版本（完整搭建步骤 + 踩坑记录）
```

## 📜 License

MIT © estella333
