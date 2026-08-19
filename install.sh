#!/usr/bin/env bash
# =============================================================
#  Obsidian 主页仪表盘 —— 一键安装脚本
#  https://github.com/estella333/obsidian-home-dashboard
#
#  用法:
#    bash install.sh                          # 自动定位 vault（读 Obsidian 配置）
#    bash install.sh -v "/path/to/vault"      # 指定 vault 路径
#    bash install.sh --with-study-time        # 额外安装「学习时间」统计脚本(macOS)
#    bash install.sh --no-plugins             # 不自动下载 Dataview/Homepage 插件
#    bash install.sh -i "00_Inbox" -a "附件"  # 自定义收件箱/附件文件夹名
#
#  依赖: bash3+ / python3 / curl
# =============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

VAULT=""
INBOX="00_Inbox"
ATTACH=""
WITH_STUDY_TIME=0
NO_PLUGINS=0

usage() {
  sed -n '2,14p' "$0"
  exit 0
}

# ---------- 参数解析 ----------
while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--vault) VAULT="$2"; shift 2 ;;
    -i|--inbox) INBOX="$2"; shift 2 ;;
    -a|--attach) ATTACH="$2"; shift 2 ;;
    --with-study-time) WITH_STUDY_TIME=1; shift ;;
    --no-plugins) NO_PLUGINS=1; shift ;;
    -h|--help) usage ;;
    *) echo "❓ 未知参数: $1 (用 -h 查看帮助)"; exit 1 ;;
  esac
done

command -v python3 >/dev/null || { echo "❌ 需要 python3"; exit 1; }
command -v curl >/dev/null || { echo "❌ 需要 curl"; exit 1; }

# ---------- 定位 vault ----------
if [[ -z "$VAULT" ]]; then
  VAULT=$(python3 - <<'PY'
import json, os, sys
candidates = []
if sys.platform == "darwin":
    p = os.path.expanduser("~/Library/Application Support/obsidian/obsidian.json")
elif os.name == "nt":
    p = os.path.join(os.environ.get("APPDATA", ""), "obsidian", "obsidian.json")
else:
    p = os.path.expanduser("~/.config/obsidian/obsidian.json")
try:
    with open(p, encoding="utf-8") as f:
        data = json.load(f)
    for v in data.get("vaults", {}).values():
        path = v.get("path", "")
        if path and os.path.isdir(path):
            candidates.append((bool(v.get("open")), path))
except Exception:
    pass
if not candidates:
    print("", end="")
    sys.exit(0)
# open:true 的优先，其次按名字排序取第一个
candidates.sort(key=lambda x: (not x[0], x[1].lower()))
print(candidates[0][1])
PY
)
fi

if [[ -z "$VAULT" || ! -d "$VAULT" ]]; then
  echo "❌ 没有自动定位到 Obsidian 库，请用 -v 指定路径："
  echo "   bash install.sh -v \"/Users/你的名字/你的库\""
  exit 1
fi
VAULT="${VAULT%/}"
echo "📂 目标库: $VAULT"

# ---------- 附件文件夹名（读 Obsidian 配置，未设则默认“附件”） ----------
if [[ -z "$ATTACH" ]]; then
  ATTACH=$(python3 - "$VAULT" <<'PY'
import json, os, sys
try:
    with open(os.path.join(sys.argv[1], ".obsidian", "app.json"), encoding="utf-8") as f:
        d = json.load(f)
    print(d.get("attachmentFolderPath", "附件").strip("/") or "附件")
except Exception:
    print("附件")
PY
)
fi
echo "📎 附件文件夹: $ATTACH"

# ---------- 备份已有 Home.md ----------
HOME_NOTE="$VAULT/Home.md"
if [[ -f "$HOME_NOTE" ]]; then
  BK="$HOME_NOTE.bak-$(date +%Y%m%d-%H%M%S)"
  cp "$HOME_NOTE" "$BK"
  echo "💾 已备份原 Home.md → $(basename "$BK")"
fi

# ---------- 生成 Home.md（替换占位符） ----------
python3 - "$VAULT" "$INBOX" "$ATTACH" "$SCRIPT_DIR/templates/Home.md" <<'PY'
import os, sys, urllib.parse
vault, inbox, attach, tpl_path = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(tpl_path, encoding="utf-8") as f:
    tpl = f.read()
enc = urllib.parse.quote(os.path.basename(vault))
tpl = (tpl.replace("{{VAULT_ENCODED}}", enc)
          .replace("{{INBOX_FOLDER}}", inbox)
          .replace("{{ATTACH_FOLDER}}", attach))
with open(os.path.join(vault, "Home.md"), "w", encoding="utf-8") as f:
    f.write(tpl)
print(f"✅ 已生成 Home.md（vault={os.path.basename(vault)}, inbox={inbox}, attach={attach}）")
PY

# ---------- 安装 CSS snippets 并启用 ----------
SNIP_DIR="$VAULT/.obsidian/snippets"
mkdir -p "$SNIP_DIR"
for css in homepage fix-flicker; do
  cp "$SCRIPT_DIR/snippets/$css.css" "$SNIP_DIR/$css.css"
done
python3 - "$VAULT" <<'PY'
import json, os, sys
vault = sys.argv[1]
appearance = os.path.join(vault, ".obsidian", "appearance.json")
try:
    with open(appearance, encoding="utf-8") as f:
        d = json.load(f)
except Exception:
    d = {}
enabled = list(d.get("enabledCssSnippets", []))
for s in ("homepage", "fix-flicker"):
    if s not in enabled:
        enabled.append(s)
d["enabledCssSnippets"] = enabled
with open(appearance, "w", encoding="utf-8") as f:
    json.dump(d, f, ensure_ascii=False, indent=2)
print("✅ CSS 片段已安装并启用: homepage, fix-flicker")
PY

# ---------- 检查/安装 Dataview + Homepage 插件 ----------
if [[ "$NO_PLUGINS" -eq 0 ]]; then
  MISSING=$(python3 - "$VAULT" <<'PY'
import json, os, sys
vault = sys.argv[1]
cp = os.path.join(vault, ".obsidian", "community-plugins.json")
try:
    with open(cp, encoding="utf-8") as f:
        enabled = json.load(f)
except Exception:
    enabled = []
print("\n".join(p for p in ("dataview", "homepage") if p not in enabled))
PY
)
  if [[ -n "$MISSING" ]]; then
    echo "🔌 需要插件: ${MISSING//$'\n'/ }（尝试自动下载…）"
    for pid in $MISSING; do
      case "$pid" in
        dataview) repo="blacksmithgu/obsidian-dataview" ;;
        homepage) repo="mirnovov/obsidian-homepage" ;;
      esac
      PDIR="$VAULT/.obsidian/plugins/$pid"
      mkdir -p "$PDIR"
      ok=1
      for asset in main.js manifest.json styles.css; do
        if ! curl -fsSL --connect-timeout 10 \
             "https://github.com/$repo/releases/latest/download/$asset" \
             -o "$PDIR/$asset"; then
          echo "   ⚠️  下载 ${asset} 失败（可能需要代理/手动安装）"
          ok=0
        fi
      done
      if [[ "$ok" -eq 1 ]]; then
        echo "   ✅ 已安装 $pid → .obsidian/plugins/$pid/"
      fi
    done
    python3 - "$VAULT" "$MISSING" <<'PY'
import json, os, sys
vault, missing = sys.argv[1], sys.argv[2].split()
cp = os.path.join(vault, ".obsidian", "community-plugins.json")
try:
    with open(cp, encoding="utf-8") as f:
        enabled = json.load(f)
except Exception:
    enabled = []
for pid in missing:
    if pid not in enabled:
        enabled.append(pid)
with open(cp, "w", encoding="utf-8") as f:
    json.dump(enabled, f, ensure_ascii=False, indent=2)
print("✅ 已写入 community-plugins.json")
PY
  else
    echo "✅ Dataview / Homepage 插件已就绪"
  fi
fi

# ---------- (可选) 学习时间统计脚本 + macOS 常驻 ----------
if [[ "$WITH_STUDY_TIME" -eq 1 ]]; then
  if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "⚠️  学习时间脚本依赖 macOS 的 lsappinfo，跳过（Windows/Linux 可手动轮换其他方案）"
  else
    INSTALL_DIR="$HOME/StudyTimeWatcher"
    mkdir -p "$INSTALL_DIR"
    cp "$SCRIPT_DIR/scripts/study_time_watch.py" "$INSTALL_DIR/study_time_watch.py"
    # 写入 vault 定位配置
    python3 - "$INSTALL_DIR/config.json" "$VAULT" "$ATTACH" <<'PY'
import json, os, sys
cfg, vault, attach = sys.argv[1], sys.argv[2], sys.argv[3]
with open(cfg, "w", encoding="utf-8") as f:
    json.dump({"vault": vault, "attach_folder": attach}, f, ensure_ascii=False, indent=2)
print("✅ 学习时间脚本已安装到 ~/StudyTimeWatcher/")
PY
    # LaunchAgent 常驻
    LABEL="com.obsidian-home-dashboard.studytime"
    PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
    mkdir -p "$HOME/Library/LaunchAgents"
    LOG_DIR="$HOME/Library/Logs/StudyTimeWatcher"
    mkdir -p "$LOG_DIR"
    cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$INSTALL_DIR/study_time_watch.py</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$LOG_DIR/daemon.log</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/daemon.err.log</string>
</dict>
</plist>
PLISTEOF
    launchctl unload "$PLIST" 2>/dev/null || true
    launchctl load "$PLIST" 2>/dev/null && echo "✅ 常驻服务已启动（launchctl）" \
      || echo "⚠️  请手动运行: launchctl load $PLIST"
  fi
fi

echo ""
echo "🎉 安装完成！请重启 Obsidian（Cmd/Ctrl+P → Reload app without saving），"
echo "   然后确保设置里把 Home.md 设为首页（Homepage 插件设置，或安装 homepage 插件）。"
