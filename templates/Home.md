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
const goal = Number(dv.current().goal) || 1000;

const now = dv.luxon.DateTime.now();
// 全库按「修改日期」汇总每日写作字数（排除 Home.md 本身）
const thesisFolder = (dv.current().thesis_folder || "10 projects-博论/博论初稿").replace(/\/+$/, "");
const thesisGoal = Number(dv.current().thesis_goal) || 180000;

async function dayBuckets() {
  const buckets = new Map();
  let thesisChars = 0;
  for (const p of dv.pages('""')) {
    if (p.file.path === "Home.md") continue;
    let content = "";
    try {
      content = (await dv.io.load(p.file.path)) ?? "";
    } catch (e) {}
    const day = p.file.mtime.toFormat("yyyy-MM-dd");
    buckets.set(day, (buckets.get(day) || 0) + content.replace(/\s+/g, "").length);
    if (p.file.path.startsWith(thesisFolder + "/")) {
      thesisChars += content.replace(/\s+/g, "").length;
    }
  }
  return { buckets, thesisChars };
}
const { buckets, thesisChars } = await dayBuckets();
const today = now.toFormat("yyyy-MM-dd");
const chars = buckets.get(today) || 0;
const pct = Math.min(100, Math.round((chars / goal) * 100));
const color = pct >= 100 ? "var(--color-green)" : pct >= 50 ? "var(--color-yellow)" : "var(--color-red)";
const C = 2 * Math.PI * 34;

// 固定周一到周日（luxon weekday：周一=1 … 周日=7）
let weekChars = 0;
const weekBars = [];
const monday = now.minus({ days: now.weekday - 1 }).startOf("day");
for (let i = 0; i < 7; i++) {
  const d = monday.plus({ days: i });
  const c = buckets.get(d.toFormat("yyyy-MM-dd")) || 0;
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

// 🎓 论文/长文进度：统计 thesis_folder 内所有 md 字数，目标 thesis_goal
const tPct = Math.min(100, Math.round((thesisChars / thesisGoal) * 100));
const tColor = tPct >= 100 ? "var(--color-green)" : tPct >= 50 ? "var(--color-yellow)" : "var(--color-red)";
addCard("论文进度", "🎓 长文进度", `<div class="hp-ring-wrap">
<svg width="96" height="96" viewBox="0 0 96 96">
<circle cx="48" cy="48" r="34" fill="none" stroke="var(--background-modifier-border)" stroke-width="9"/>
<circle cx="48" cy="48" r="34" fill="none" stroke="${tColor}" stroke-width="9" stroke-linecap="round" stroke-dasharray="${C}" stroke-dashoffset="${C * (1 - tPct / 100)}" transform="rotate(-90 48 48)"/>
<text x="48" y="53" text-anchor="middle" font-size="18" font-weight="700" fill="var(--text-normal)">${tPct}%</text>
</svg>
<div class="hp-ring-label">${thesisChars.toLocaleString()} / ${thesisGoal.toLocaleString()} 字</div></div>`);

// 📝 便签：直接点击输入，自动保存到 {{ATTACH_FOLDER}}/home-memo.txt（txt 不影响字数统计）
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

// ⏱️ 学习时间：今日学习 App 使用总时长（可选功能）
// 数据由后台脚本 scripts/study_time_watch.py 每 10 分钟写入 {{ATTACH_FOLDER}}/study-time.json；
// 没装该脚本时此卡显示 0。
let st = { today_seconds: 0 };
try { st = Object.assign(st, JSON.parse((await dv.io.load("{{ATTACH_FOLDER}}/study-time.json")) ?? "{}")); } catch (e) {}
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

// —— 拖拽排序：恢复上次保存的顺序，并绑定拖拽事件 ——
const ORDER_KEY = "hp-card-order-" + (app.vault.getName() || "default");
const defaultOrder = ["今日进度", "本周写作", "论文进度", "便签", "库统计", "学习时间"];
let savedOrder = [];
try { savedOrder = JSON.parse(localStorage.getItem(ORDER_KEY) || "[]"); } catch (e) {}
const order = defaultOrder.filter(k => savedOrder.includes(k)).concat(defaultOrder.filter(k => !savedOrder.includes(k)));
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
    if (!dragKey || dragKey === card.dataset.key) return;
    const src = cards[dragKey], dst = cards[card.dataset.key];
    const kids = Array.from(grid.children);
    if (kids.indexOf(src) < kids.indexOf(dst)) grid.insertBefore(src, dst.nextSibling);
    else grid.insertBefore(src, dst);
    try { localStorage.setItem(ORDER_KEY, JSON.stringify(Array.from(grid.children).map(c => c.dataset.key))); } catch (err) {}
  });
  card.addEventListener("dragend", () => { card.style.opacity = ""; card.style.outline = ""; dragKey = null; });
});
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
// 认识常见目录结构时显示对应图标，其他文件夹显示 📄
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
