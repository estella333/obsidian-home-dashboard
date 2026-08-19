---
tags:
  - index
cssclasses:
  - homepage
# ✏️ 每日写作字数目标（改这个数字即可）
goal: 1000
# 🎓 论文/长文进度卡：folder 为统计的文件夹（相对 vault 根），goal 为目标字数。
# 不需要这张卡的话，删掉下面两行，并删除正文里「论文进度」那一段代码。
thesis_folder: 10 projects-博论/博论初稿
thesis_goal: 180000
# ⏱️ 学习时间卡（可选）：study_json_path 填学习时间 JSON 的绝对路径（如 macOS 应用数据目录），
# 不填则自动读 vault 附件下的 study-time.json。
study_json_path: ""
---

```dataviewjs
// ===== 问候语 + 日期 =====
const now = dv.luxon.DateTime.now();
const h = now.hour;
const greet = h < 5 ? "夜深了，早点休息" : h < 9 ? "早上好" : h < 12 ? "上午好" : h < 14 ? "中午好" : h < 18 ? "下午好" : "晚上好";
const week = ["日", "一", "二", "三", "四", "五", "六"][now.weekday % 7];
const hero = dv.container.createEl("div", { cls: "hp-hero" });
hero.createEl("div", { cls: "hp-greet", text: `${greet} 👋` });
hero.createEl("div", { cls: "hp-date", text: `${now.year} 年 ${now.month} 月 ${now.day} 日 · 星期${week}` });
```

<div class="hp-actions">

<a class="hp-btn" href="obsidian://new?vault={{VAULT_ENCODED}}&file={{INBOX_FOLDER}}/%E5%BF%AB%E9%80%9F%E7%AC%94%E8%AE%B0&paneType=tab">⚡ 快速记笔记</a>

<a class="hp-btn alt" href="obsidian://daily?vault={{VAULT_ENCODED}}&paneType=tab">📅 今日日记</a>

</div>

```dataviewjs
// ===== 统计卡片 =====
// ✏️ 每日字数目标：改本文件头部属性（Properties）里的 goal 数值即可，默认 1000
const goal = Number(dv.current().goal) || 1000;

const now = dv.luxon.DateTime.now();
// 实时字数统计：每天首次渲染时把全库内容存为快照（{{ATTACH_FOLDER}}/daily-snapshot.json），
// 之后每次渲染把当前内容与快照做字符级 diff = 「今天真正新增的字数」——
// 旧文件改几个字只算几个字，纯页面内计算，实时同步，无需外部脚本/定时任务。
// 跨天时自动轮换快照并把前一天增量记入历史（供本周图表用）。
// 论文初稿文件夹：在本文件头部属性 thesis_folder / thesis_goal 修改
const thesisFolder = (dv.current().thesis_folder || "10 projects-博论/博论初稿").replace(/\/+$/, "");
const thesisGoal = Number(dv.current().thesis_goal) || 180000;

const SNAP_PATH = "{{ATTACH_FOLDER}}/daily-snapshot.json";
let today = now.toFormat("yyyy-MM-dd");

function countNonWs(s) { return (s || "").replace(/\s+/g, "").length; }
// 字符粒度增量：base → cur 新增的非空白字符数（顺序贪心匹配；超 3 万字的大文件用长度差近似，防卡顿）
function addedChars(cur, base) {
  if (!base) return countNonWs(cur);
  if (!cur) return 0;
  if (base.length > 30000 || cur.length > 30000) return Math.max(0, countNonWs(cur) - countNonWs(base));
  let added = 0, j = 0, n = cur.length;
  for (let i = 0; i < base.length; i++) {
    const ch = base[i];
    if (ch === " " || ch === "\n" || ch === "\t" || ch === "\r") continue;
    const idx = cur.indexOf(ch, j);
    if (idx === -1) { added += countNonWs(cur.slice(j)); j = n; break; }
    added += countNonWs(cur.slice(j, idx));
    j = idx + 1;
  }
  if (j < n) added += countNonWs(cur.slice(j));
  return added;
}

// 读取全部 md 内容（排除 Home.md）；useCache=true 走 Obsidian 缓存（快速刷新用）
async function loadAll(useCache) {
  const map = {};
  for (const f of app.vault.getFiles()) {
    if (!f.path.endsWith(".md") || f.path === "Home.md") continue;
    try { map[f.path] = useCache ? await app.vault.cachedRead(f) : ((await dv.io.load(f.path)) ?? ""); }
    catch (e) { map[f.path] = ""; }
  }
  return map;
}

let snap = null;
try { snap = JSON.parse((await dv.io.load(SNAP_PATH)) ?? "null"); } catch (e) {}
if (!snap || typeof snap !== "object") snap = { date: "", files: {}, history: {} };
if (!snap.files) snap.files = {};
if (!snap.history) snap.history = {};

let contents = await loadAll(false);
let live = { total: 0, perFile: {} };
if (snap.date === today && Object.keys(snap.files).length > 0) {
  for (const [path, cur] of Object.entries(contents)) {
    const d = addedChars(cur, snap.files[path] || "");
    if (d > 0) { live.perFile[path] = d; live.total += d; }
  }
} else {
  // 新的一天（或首次运行）：旧快照→现在的增量记入历史，再以当前内容为新快照
  if (snap.date && snap.date !== today && Object.keys(snap.files).length > 0) {
    let oldTotal = 0;
    for (const [path, cur] of Object.entries(contents)) oldTotal += addedChars(cur, snap.files[path] || "");
    snap.history[snap.date] = oldTotal;
  }
  snap = { date: today, files: contents, history: snap.history };
  try { await app.vault.adapter.write(SNAP_PATH, JSON.stringify(snap)); } catch (e) {}
}

const chars = live.total;
let thesisChars = 0;
for (const [path, c] of Object.entries(contents)) {
  if (path.startsWith(thesisFolder + "/")) thesisChars += countNonWs(c);
}
const pct = Math.min(100, Math.round((chars / goal) * 100));
const color = pct >= 100 ? "var(--color-green)" : pct >= 50 ? "var(--color-yellow)" : "var(--color-red)";
const C = 2 * Math.PI * 34;

// 固定周一到周日（luxon weekday：周一=1 … 周日=7）；过去天数用快照历史，今天用实时增量
let weekChars = 0;
let weekBars = [];
const monday = now.minus({ days: now.weekday - 1 }).startOf("day");
for (let i = 0; i < 7; i++) {
  const d = monday.plus({ days: i });
  const key = d.toFormat("yyyy-MM-dd");
  const c = key === today ? chars : (snap.history[key] || 0);
  weekChars += c;
  weekBars.push({ label: ["一", "二", "三", "四", "五", "六", "日"][i], c });
}
const maxC = Math.max(...weekBars.map(b => b.c), 1);

const pages = dv.pages('""');
const inboxCount = dv.pages('"{{INBOX_FOLDER}}"').length;

const grid = dv.container.createEl("div", { cls: "hp-grid" });
const cards = {};
// 四张卡都可拖拽换位：按住卡片拖动到目标位置松手即可，顺序自动记住（刷新后保持）
const addCard = (key, title, html, extraCls = "") => {
  const el = grid.createEl("div", { cls: ("hp-card " + extraCls).trim() });
  el.dataset.key = key;
  el.createEl("div", { cls: "hp-card-title", text: title });
  const body = el.createEl("div", { cls: "hp-card-body" });
  body.innerHTML = html;
  cards[key] = el;
  return el;
};

addCard("今日进度", "📝 今日进度", `<div class="hp-ring-wrap">
<svg width="96" height="96" viewBox="0 0 96 96">
<circle cx="48" cy="48" r="34" fill="none" stroke="var(--background-modifier-border)" stroke-width="9"/>
<circle cx="48" cy="48" r="34" fill="none" stroke="${color}" stroke-width="9" stroke-linecap="round" stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - pct / 100)}" transform="rotate(-90 48 48)"/>
<text x="48" y="53" text-anchor="middle" font-size="18" font-weight="700" fill="var(--text-normal)">${pct}%</text>
</svg>
<div class="hp-ring-label">${chars} / ${goal} 字</div></div>`);

addCard("本周写作", "📈 本周写作（每日字数）", `<div class="hp-bars">${weekBars.map((b, i) => `<div class="hp-bar-col${i === now.weekday - 1 ? " today" : ""}"><div class="hp-bar-num">${b.c > 0 ? b.c : ""}</div><div class="hp-bar" style="height:${Math.max(5, Math.round((b.c / maxC) * 60))}px" title="${b.c} 字"></div><div class="hp-bar-label">${b.label}</div></div>`).join("")}</div><div class="hp-bars-note">本周共 ${weekChars} 字</div>`);

addCard("库统计", "📊 库统计", `<div class="hp-stats-row">
<div class="hp-stat"><div class="hp-num">${pages.length}</div><div class="hp-num-label">全库笔记</div></div>
<div class="hp-stat"><div class="hp-num">${inboxCount}</div><div class="hp-num-label">收件箱待整理</div></div>
</div>`);

// 🎓 长文进度：统计 thesis_folder 内所有 md 字数，目标 thesis_goal
const tPct = Math.min(100, Math.round((thesisChars / thesisGoal) * 100));
const tColor = tPct >= 100 ? "var(--color-green)" : tPct >= 50 ? "var(--color-yellow)" : "var(--color-red)";
addCard("论文进度", "🎓 长文进度", `<div class="hp-ring-wrap">
<svg width="96" height="96" viewBox="0 0 96 96">
<circle cx="48" cy="48" r="34" fill="none" stroke="var(--background-modifier-border)" stroke-width="9"/>
<circle cx="48" cy="48" r="34" fill="none" stroke="${tColor}" stroke-width="9" stroke-linecap="round" stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - tPct / 100)}" transform="rotate(-90 48 48)"/>
<text x="48" y="53" text-anchor="middle" font-size="18" font-weight="700" fill="var(--text-normal)">${tPct}%</text>
</svg>
<div class="hp-ring-label">${thesisChars.toLocaleString()} / ${thesisGoal.toLocaleString()} 字</div></div>`);

// 📝 便签：直接点击输入，自动保存到 {{ATTACH_FOLDER}}/home-memo.txt（txt 不影响字数统计，git 自动备份）
const MEMO_PATH = "{{ATTACH_FOLDER}}/home-memo.txt";
let memoText = "";
try { memoText = (await app.vault.adapter.read(MEMO_PATH)) ?? ""; } catch (e) { memoText = ""; }
const escMemo = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
addCard("便签", "📝 便签", `<textarea class="hp-memo" placeholder="✍️ 临时备忘，随便记…">${escMemo(memoText)}</textarea>`);
{
  const mc = cards["便签"];
  mc.querySelector(".hp-card-body").classList.add("memo-body");
  const ta = mc.querySelector(".hp-memo");
  let saveTimer = null;
  ta.addEventListener("input", () => {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(async () => {
      try { await app.vault.adapter.write(MEMO_PATH, ta.value); } catch (e) {}
    }, 800);
  });
}

// ⏱️ 学习时间：今日 Obsidian / Typora / 预览 使用总时长
// 数据由后台脚本 study_time_watch.py 每 10 分钟写入。优先读应用数据目录
// （~/Library/Application Support/StudyTime/study-time.json，launchd 环境无 TCC 限制），
// 失败则回退 vault 内 {{ATTACH_FOLDER}}/study-time.json（脚本能写时也会同步写一份）
let st = { today_seconds: 0 };
// 学习时间 JSON 优先读 frontmatter study_json_path 指定的绝对路径（如 macOS 应用数据目录），
// 未配置则读 vault 附件（后台脚本双写，两处都有）
const ST_APP_PATH = (dv.current().study_json_path || "").toString().trim();
try {
  if (!ST_APP_PATH) throw new Error("no app path");
  st = Object.assign(st, JSON.parse(await app.vault.adapter.read(ST_APP_PATH)));
} catch (e) {
  try { st = Object.assign(st, JSON.parse((await dv.io.load("{{ATTACH_FOLDER}}/study-time.json")) ?? "{}")); } catch (e2) {}
}
const m = Math.round((st.today_seconds || 0) / 60);
const tStr = m >= 60 ? `${Math.floor(m / 60)}h ${m % 60}m` : `${m}m`;
const tFs = tStr.length > 5 ? 15 : 17;
addCard("学习时间", "⏱️ 学习时间", `<div class="hp-ring-wrap">
<svg width="96" height="96" viewBox="0 0 96 96">
<circle cx="48" cy="48" r="34" fill="none" stroke="var(--background-modifier-border)" stroke-width="9"/>
<circle cx="48" cy="48" r="34" fill="none" stroke="var(--interactive-accent)" stroke-width="9" stroke-linecap="round" stroke-dasharray="${C}" transform="rotate(-90 48 48)"/>
<text x="48" y="53" text-anchor="middle" font-size="${tFs}" font-weight="700" fill="var(--text-normal)">${tStr}</text>
</svg>
<div class="hp-ring-label">今日学习</div></div>`);

// —— 拖拽排序：顺序保存到 {{ATTACH_FOLDER}}/home-card-order.json（本地文件，重启/换设备都保持），localStorage 仅作兜底 ——
const ORDER_KEY = "hp-card-order-" + (app.vault.getName() || "default");
const ORDER_FILE = "{{ATTACH_FOLDER}}/home-card-order.json";
const defaultOrder = ["今日进度", "本周写作", "论文进度", "便签", "库统计", "学习时间"];
async function loadSavedOrder() {
  try {
    const raw = await app.vault.adapter.read(ORDER_FILE);
    const arr = JSON.parse(raw);
    if (Array.isArray(arr)) return arr;
  } catch (e) {}
  try {
    const legacy = JSON.parse(localStorage.getItem(ORDER_KEY) || "[]");
    if (Array.isArray(legacy)) return legacy;
  } catch (e) {}
  return [];
}
async function saveOrderNow() {
  const order = Array.from(grid.children).map(c => c.dataset.key);
  try { await app.vault.adapter.write(ORDER_FILE, JSON.stringify(order)); } catch (e) {}
  try { localStorage.setItem(ORDER_KEY, JSON.stringify(order)); } catch (e) {}
}
const savedOrder = await loadSavedOrder();
// 按保存的顺序原样恢复（保存什么顺序就恢复什么顺序），未保存过的卡片追加到末尾
const order = savedOrder.filter(k => cards[k]).concat(defaultOrder.filter(k => !savedOrder.includes(k)));
order.forEach(k => { if (cards[k]) grid.appendChild(cards[k]); });

let dragKey = null;
Object.values(cards).forEach(card => {
  card.draggable = true;
  card.addEventListener("dragstart", e => {
    dragKey = card.dataset.key;
    card.style.opacity = "0.4";
    card.style.outline = "2px dashed var(--interactive-accent)";
    try { e.dataTransfer.setData("text/plain", dragKey); e.dataTransfer.effectAllowed = "move"; } catch (err) {}
  });
  card.addEventListener("dragover", e => { e.preventDefault(); try { e.dataTransfer.dropEffect = "move"; } catch (err) {} });
  card.addEventListener("drop", e => {
    e.preventDefault();
    e.stopPropagation();
    if (!dragKey || dragKey === card.dataset.key) return;
    const src = cards[dragKey], dst = cards[card.dataset.key];
    const kids = Array.from(grid.children);
    if (kids.indexOf(src) < kids.indexOf(dst)) grid.insertBefore(src, dst.nextSibling);
    else grid.insertBefore(src, dst);
    saveOrderNow();
  });
  card.addEventListener("dragend", () => {
    card.style.opacity = "";
    card.style.outline = "";
    dragKey = null;
    saveOrderNow();
  });
});

// —— 实时刷新：每 30 秒用缓存重算今日字数并更新卡片（视图关闭后自动停止）——
let todayIdx = now.weekday - 1;
const todayWrap = cards["今日进度"].querySelector(".hp-ring-wrap");
const todayRing = cards["今日进度"].querySelector("svg circle:nth-of-type(2)");
const todayText = cards["今日进度"].querySelector("svg text");
const todayLabel = cards["今日进度"].querySelector(".hp-ring-label");
const barEls = Array.from(cards["本周写作"].querySelectorAll(".hp-bar"));
const barNums = Array.from(cards["本周写作"].querySelectorAll(".hp-bar-num"));
const barsNote = cards["本周写作"].querySelector(".hp-bars-note");

// —— 悬停明细：自绘 tooltip（Obsidian 原生 title 提示不可靠，自绘跟随鼠标的多行提示）——
document.querySelectorAll(".hp-tip").forEach(el => el.remove()); // 清掉上次渲染残留（重渲染会新建）
const tipEl = document.body.createEl("div", { cls: "hp-tip" });
tipEl.style.cssText = "position:fixed;z-index:9999;display:none;max-width:360px;background:var(--background-primary);border:1px solid var(--background-modifier-border);border-radius:8px;padding:8px 12px;font-size:12px;line-height:1.7;box-shadow:0 4px 16px rgba(0,0,0,.18);pointer-events:none;word-break:break-all;";
const tipTitle = tipEl.createEl("div", { text: "", cls: "hp-tip-title" });
tipTitle.style.cssText = "font-weight:600;margin-bottom:4px;";
const tipList = tipEl.createEl("div", { cls: "hp-tip-list" });
function updateTip() {
  const rows = Object.entries(live.perFile).sort((a, b) => b[1] - a[1]).slice(0, 12);
  tipTitle.textContent = `📝 今日共 ${live.total} 字`;
  tipList.empty();
  if (!rows.length) { tipList.createEl("div", { text: "今天还没有新增字数" }); return; }
  rows.forEach(([f, c]) => tipList.createEl("div", { text: `${f}：${c} 字` }));
}
function positionTip(e) {
  tipEl.style.left = Math.max(8, Math.min(e.clientX + 14, window.innerWidth - 380)) + "px";
  tipEl.style.top = (e.clientY + 18) + "px";
}
todayWrap.addEventListener("mouseenter", e => { updateTip(); tipEl.style.display = "block"; positionTip(e); });
todayWrap.addEventListener("mousemove", e => positionTip(e));
todayWrap.addEventListener("mouseleave", () => { tipEl.style.display = "none"; });

function refreshBars() {
  const mx = Math.max(...weekBars.map(b => b.c), 1);
  barEls.forEach((el, i) => {
    const b = weekBars[i] || { c: 0 };
    el.style.height = Math.max(5, Math.round((b.c / mx) * 60)) + "px";
    el.title = b.c + " 字";
    if (barNums[i]) barNums[i].textContent = b.c > 0 ? b.c : "";
  });
  barsNote.textContent = `本周共 ${weekBars.reduce((s, x) => s + x.c, 0)} 字`;
}

function renderToday() {
  const p2 = Math.min(100, Math.round((live.total / goal) * 100));
  const c2 = p2 >= 100 ? "var(--color-green)" : p2 >= 50 ? "var(--color-yellow)" : "var(--color-red)";
  todayRing.setAttribute("stroke-dashoffset", (C * (1 - p2 / 100)).toFixed(1));
  todayRing.setAttribute("stroke", c2);
  todayText.textContent = p2 + "%";
  todayLabel.textContent = `${live.total} / ${goal} 字`;
  updateTip();
  if (weekBars[todayIdx]) weekBars[todayIdx].c = live.total;
  refreshBars();
}

setInterval(async () => {
  try {
    if (!grid.isConnected) return; // 视图已关闭（dataview 重渲染后旧定时器随旧 DOM 丢弃）
    const tNow = dv.luxon.DateTime.now();
    const tToday = tNow.toFormat("yyyy-MM-dd");
    if (tToday !== today) {
      // 跨天：旧快照→现在的增量记入历史，轮换快照，今天从 0 开始
      const c2 = await loadAll(false);
      if (snap.date && snap.date !== tToday && Object.keys(snap.files).length > 0) {
        let oldTotal = 0;
        for (const [p, cu] of Object.entries(c2)) oldTotal += addedChars(cu, snap.files[p] || "");
        snap.history[snap.date] = oldTotal;
      }
      snap = { date: tToday, files: c2, history: snap.history || {} };
      try { await app.vault.adapter.write(SNAP_PATH, JSON.stringify(snap)); } catch (e) {}
      today = tToday;
      live = { total: 0, perFile: {} };
      todayIdx = tNow.weekday - 1;
      const mm = tNow.minus({ days: tNow.weekday - 1 }).startOf("day");
      weekBars = [];
      for (let i = 0; i < 7; i++) {
        const dd = mm.plus({ days: i });
        const kk = dd.toFormat("yyyy-MM-dd");
        const cc = kk === tToday ? 0 : (snap.history[kk] || 0);
        weekBars.push({ label: ["一", "二", "三", "四", "五", "六", "日"][i], c: cc });
      }
      renderToday();
      return;
    }
    const c = await loadAll(true);
    live = { total: 0, perFile: {} };
    for (const [path, cur] of Object.entries(c)) {
      const d = addedChars(cur, snap.files[path] || "");
      if (d > 0) { live.perFile[path] = d; live.total += d; }
    }
    renderToday();
  } catch (e) {}
}, 30000);
```

## 🕘 最近打开

```dataviewjs
// 最近打开：只显示笔记标题 + 文件夹图标，不显示路径
const me = dv.current().file.path;
let opened = app.workspace.getLastOpenFiles()
  .filter(f => f.endsWith(".md") && f !== me && f !== "Home.md")
  .slice(0, 5);
if (opened.length < 3) {
  const fallback = dv.pages('""')
    .where(p => p.file.path !== me && p.file.name !== "Home")
    .sort(p => p.file.mtime, "desc")
    .map(p => p.file.path).values;
  for (const f of fallback) {
    if (!opened.includes(f)) opened.push(f);
    if (opened.length >= 5) break;
  }
}
opened = opened.slice(0, 5);
const icons = {
  "00_Inbox": "📥",
  "10 projects-博论": "🎓",
  "20 project-小论文": "🚀",
  "30 areas-文献积累": "📚",
  "40 archive": "📦",
  "50 ideas": "💡",
  "60 index": "🗂️"
};
const wrap = dv.container.createEl("div", { cls: "hp-recent" });
opened.forEach(f => {
  const tf = app.vault.getAbstractFileByPath(f);
  if (!tf) return;
  const folder = tf.path.includes("/") ? tf.path.split("/").slice(0, -1).join("/") : "";
  const icon = icons[folder] ?? "📄";
  const cleanPath = tf.path.replace(/\.md$/, "");
  const item = wrap.createEl("div", { cls: "hp-recent-item" });
  item.innerHTML = `<span class="hp-recent-icon">${icon}</span><a class="internal-link" data-href="${cleanPath}" href="${cleanPath}">${tf.basename}</a>`;
});
```
