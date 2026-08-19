#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
学习时间统计守护进程
====================
每 10 秒检测一次前台 App，统计 Obsidian / Typora / 预览(Preview) 的
使用时长（写笔记/读文献的学习时间），聚合结果写入 Obsidian vault 的
「附件/study-time.json」，供 Home.md 的 dataviewjs 读取展示。

CPU 占用：<0.1%（大多数时间 sleep，仅每 10 秒跑一条 lsappinfo 命令）
磁盘占用：每天几 KB 追加日志

用法：
  python3 study_time_watch.py          守护模式（配合 LaunchAgent 常驻）
  python3 study_time_watch.py --once   打印当前前台 App 的 bundle id（自检用）
  python3 study_time_watch.py --stats  立即重算统计并退出（手动刷新用）

可配置项（直接改下面常量即可）：
  TARGETS    要统计的 App（bundle id -> 显示名）
  POLL_SEC   轮询间隔（秒），默认 10；改大更省资源，改小更精确
  STATS_EVERY  每多少秒重算一次统计并写入 vault（默认 600 = 10 分钟）
"""
import fcntl
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timedelta

# ===== 配置 =====
TARGETS = {
    "md.obsidian.Obsidian": "Obsidian",
    "abnerworks.Typora": "Typora",
    "com.apple.Preview": "预览",
}
POLL_SEC = 10          # 轮询间隔（秒）
STATS_EVERY = 600      # 每 600 秒重算一次统计写 vault
STATE_EVERY = 60       # 每 60 秒落盘一次「进行中会话」快照（防崩溃丢失）
GAP_SEC = POLL_SEC * 3 # 相邻两次检测间隔超过此值视为睡眠/挂起，间隔不计时

DATA_DIR = os.path.expanduser("~/Library/Application Support/StudyTime")
LOG_PATH = os.path.join(DATA_DIR, "usage_log.jsonl")   # 已完成会话（追加）
STATE_PATH = os.path.join(DATA_DIR, "state.json")      # 进行中会话（崩溃恢复）
LOCK_PATH = os.path.join(DATA_DIR, "watch.lock")

# vault 定位（按优先级）：
#   1) 环境变量 OBSIDIAN_VAULT_PATH
#   2) install.sh 生成的 ~/Library/Application Support/StudyTime/config.json
#   3) Obsidian 配置中 open:true 的 vault（单库场景即唯一库）
# 附件文件夹名同样从上述来源读取，默认 "附件"。
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
FALLBACK_STATS_PATH = os.path.expanduser(
    "~/Desktop/笔记文件存放/朵朵的知识库/附件/study-time.json")


def vault_stats_path():
    # 1) 环境变量
    env = os.environ.get("OBSIDIAN_VAULT_PATH")
    if env and os.path.isdir(env):
        return os.path.join(env, "附件", "study-time.json")
    # 2) install.sh 写入的配置
    try:
        with open(CONFIG_PATH, "r") as f:
            cfg = json.load(f)
        vault = cfg.get("vault", "")
        attach = cfg.get("attach_folder", "附件")
        if vault and os.path.isdir(vault):
            return os.path.join(vault, attach, "study-time.json")
    except Exception:
        pass
    # 3) Obsidian 配置：优先 open:true 的库
    try:
        p = os.path.expanduser("~/Library/Application Support/obsidian/obsidian.json")
        with open(p, "r") as f:
            data = json.load(f)
        for v in data.get("vaults", {}).values():
            if v.get("open") and os.path.isdir(v.get("path", "")):
                return os.path.join(v["path"], "附件", "study-time.json")
        for v in data.get("vaults", {}).values():
            if os.path.isdir(v.get("path", "")):
                return os.path.join(v["path"], "附件", "study-time.json")
    except Exception:
        pass
    return FALLBACK_STATS_PATH


def front_app():
    """返回当前前台 App 的 bundle id；失败返回 None。"""
    try:
        out = subprocess.run(["lsappinfo", "front"], capture_output=True,
                             text=True, timeout=3).stdout.strip()
        asn = out.split()[0] if out else ""
        if not asn.startswith("ASN:"):
            return None
        out2 = subprocess.run(["lsappinfo", "info", "-only", "bundleID", asn],
                              capture_output=True, text=True, timeout=3).stdout
        if "CFBundleIdentifier" in out2:
            return out2.split("=", 1)[1].strip().strip('"')
    except Exception:
        pass
    return None


# ===== 数据读写 =====
def load_sessions():
    sessions = []
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    sessions.append(json.loads(line))
                except Exception:
                    pass
    return sessions


def append_session(app, start_ts, end_ts):
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps({"app": app, "s": start_ts, "e": end_ts}) + "\n")


def write_state(app, start_ts, now_ts):
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"app": app, "s": start_ts, "e": now_ts}, f)
    os.replace(tmp, STATE_PATH)


def read_state():
    try:
        with open(STATE_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return None


# ===== 聚合 =====
def split_by_day(start_ts, end_ts):
    """把一段会话按自然日切分，返回 [(日期, 秒数)]"""
    out = []
    cur = start_ts
    while cur < end_ts:
        d = datetime.fromtimestamp(cur).date()
        nxt_date = d + timedelta(days=1)
        nxt = min(end_ts, datetime(nxt_date.year, nxt_date.month, nxt_date.day).timestamp())
        out.append((d.isoformat(), max(0, int(nxt - cur))))
        cur = nxt
    return out


def aggregate(sessions, state=None, now_ts=None):
    """按天+按 App 汇总秒数。同一时刻只有一个前台 App，直接相加即可。"""
    daily = {}
    all_sess = list(sessions)
    if state and state.get("app") and state.get("s") and state.get("e"):
        s, e = state["s"], state.get("e", now_ts or time.time())
        # 快照过于陈旧（守护进程停止过）→ 只认到快照时刻，避免把停机时间算进去
        if (now_ts or time.time()) - e > 600:
            e = s
        if e > s:
            all_sess.append({"app": state["app"], "s": s, "e": e})
    for s in all_sess:
        app, st, en = s.get("app"), s.get("s"), s.get("e")
        if not app or not st or not en or en <= st:
            continue
        for ds, sec in split_by_day(st, en):
            daily.setdefault(ds, {}).setdefault(app, 0)
            daily[ds][app] += sec
    return daily


def build_stats(daily, now=None):
    now = now or datetime.now()
    today = now.date()

    def day_sec(d):
        d = d.isoformat()
        return sum(daily.get(d, {}).values()) if daily.get(d) else 0

    week = [{"date": (today - timedelta(days=i)).isoformat(),
             "seconds": day_sec(today - timedelta(days=i))} for i in range(6, -1, -1)]
    month = [{"date": (today - timedelta(days=i)).isoformat(),
              "seconds": day_sec(today - timedelta(days=i))} for i in range(29, -1, -1)]

    streak = 0
    d = today
    if day_sec(d) == 0:
        d -= timedelta(days=1)
    while day_sec(d) > 0:
        streak += 1
        d -= timedelta(days=1)

    return {
        "updated_ts": int(time.time()),
        "today": today.isoformat(),
        "today_seconds": day_sec(today),
        "apps_today": dict(sorted(
            ((TARGETS.get(k, k), v) for k, v in daily.get(today.isoformat(), {}).items()),
            key=lambda kv: -kv[1])),
        "week": week,
        "month": month,
        "streak_days": streak,
    }


def recompute():
    sessions = load_sessions()
    daily = aggregate(sessions, read_state(), time.time())
    stats = build_stats(daily)
    path = vault_stats_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(stats, f, ensure_ascii=False)
    os.replace(tmp, path)
    return stats


# ===== 主循环 =====
def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    # 单实例锁
    lock_fd = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("already running, exit", file=sys.stderr)
        sys.exit(0)

    stopping = {"v": False}
    def stop(*_):
        stopping["v"] = True
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    # 崩溃恢复：若上次快照距今 ≤60 秒则接着算，否则把快照段落盘并重新开始
    cur_app, cur_start = None, None
    state = read_state()
    if state and state.get("app") and state.get("s"):
        now = time.time()
        if now - state.get("e", now) <= 60:
            cur_app, cur_start = state["app"], state["s"]
        else:
            e = state.get("e", state["s"])
            if e > state["s"] and state["app"] in TARGETS:
                append_session(state["app"], state["s"], e)

    last_state_ts = last_stats_ts = 0.0
    last_tick = time.time()

    while not stopping["v"]:
        t = time.time()
        # 睡眠/挂起检测：间隔远超轮询周期说明机器睡过，间隔时间不计入
        if t - last_tick > GAP_SEC:
            if cur_app in TARGETS and cur_start is not None:
                append_session(cur_app, cur_start, last_tick)
            cur_start = t if cur_app else None
        last_tick = t

        app = front_app()
        if app != cur_app:
            if cur_app in TARGETS and cur_start is not None:
                append_session(cur_app, cur_start, t)
            cur_app, cur_start = app, (t if app else None)
            if app in TARGETS and cur_start is not None:
                write_state(app, cur_start, t)

        if cur_app in TARGETS and cur_start is not None and t - last_state_ts >= STATE_EVERY:
            write_state(cur_app, cur_start, t)
            last_state_ts = t

        if t - last_stats_ts >= STATS_EVERY:
            recompute()
            last_stats_ts = t

        time.sleep(POLL_SEC)

    # 收尾
    if cur_app in TARGETS and cur_start is not None:
        append_session(cur_app, cur_start, time.time())
    recompute()


if __name__ == "__main__":
    if "--once" in sys.argv:
        print(front_app())
    elif "--stats" in sys.argv:
        s = recompute()
        print(json.dumps(s, ensure_ascii=False, indent=2))
    else:
        main()
