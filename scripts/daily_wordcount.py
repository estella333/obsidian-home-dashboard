#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日写作字数统计（git 增量版）
============================
vault 由 obsidian-git 每 ~10 分钟自动提交。本脚本用
`git diff --word-diff=plain --word-diff-regex=.` 按「字符粒度」统计
每个自然日真正新增的字数（旧文件里改几个字只算几个字，不再整篇计）。

写入 ~/Library/Application Support/StudyTime/daily-wordcount.json
（launchd/cron 环境无 TCC 限制的主路径），并尽力同步一份到 vault 附件/
（被 TCC 拦截时忽略，不影响主数据）。Home.md 的 dataviewjs 优先读主路径。

用法:
  python3 daily_wordcount.py           计算并写入（定时任务模式）
  python3 daily_wordcount.py --print   计算并打印 JSON（自检用）

调度注意：
  vault 若位于 ~/Desktop 等 TCC 保护目录，launchd 后台进程读不了 vault（git
  报 "Unable to read current working directory" / Permission denied），必须改用
  有桌面权限的调度器（如 Hermes cron）运行本脚本。
"""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta

DATA_DIR = os.path.expanduser("~/Library/Application Support/StudyTime")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
GIT = "/usr/bin/git"
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
# 只统计 .md；排除 Home.md（仪表盘本身）、.obsidian 配置、附件目录
MD_PATHS = ["*.md", ":!Home.md", ":!.obsidian", ":!附件"]


def find_vault():
    """定位 vault：config.json > obsidian.json(open:true 优先)"""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg = json.load(f)
        v = cfg.get("vault", "")
        if v and os.path.isdir(v):
            return v
    except Exception:
        pass
    try:
        with open(os.path.expanduser("~/Library/Application Support/obsidian/obsidian.json"),
                  encoding="utf-8") as f:
            data = json.load(f)
        for v in data.get("vaults", {}).values():
            if v.get("open") and os.path.isdir(v.get("path", "")):
                return v["path"]
        for v in data.get("vaults", {}).values():
            if os.path.isdir(v.get("path", "")):
                return v["path"]
    except Exception:
        pass
    return None


def git(vault, args):
    r = subprocess.run([GIT, "-c", "core.quotepath=false", "-C", vault] + args,
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:300])
    return r.stdout


def last_commit_before(vault, before_iso):
    """before_iso 时刻之前的最后一个提交；仓库无提交时用空树"""
    out = git(vault, ["log", "-1", "--before=" + before_iso, "--format=%H"]).strip()
    return out or EMPTY_TREE


def added_chars(vault, base, head):
    """base..head 之间真正新增的非空白字符数（按文件拆分）"""
    if base == head:
        return 0, {}
    out = git(vault, ["diff", base, head, "--word-diff=plain",
                      "--word-diff-regex=.", "--"] + MD_PATHS)
    total = 0
    per_file = {}
    cur = None
    for line in out.splitlines():
        if line.startswith("diff --git"):
            m = re.search(r" b/(.+)$", line)
            cur = m.group(1) if m else None
        elif cur:
            cnt = 0
            for frag in re.findall(r"\{\+([^+]*)\+\}", line):
                cnt += len(re.sub(r"\s+", "", frag))
            if cnt:
                per_file[cur] = per_file.get(cur, 0) + cnt
                total += cnt
    return total, per_file


def compute_week(vault, today):
    week = {}
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        ds = d.isoformat()
        base = last_commit_before(vault, ds + " 00:00:00")
        if d == today:
            head = "HEAD"  # 当天进行中：算到最新提交
        else:
            head = last_commit_before(vault, ds + " 23:59:59")
        n, _ = added_chars(vault, base, head)
        week[ds] = n
    return week


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, path)


def main():
    vault = find_vault()
    if not vault:
        print("vault not found", file=sys.stderr)
        sys.exit(1)
    # 先进到 vault 再跑 git：避免启动时 cwd 不可读（launchd 无桌面 TCC 权限时报
    # "Unable to read current working directory"）。若 vault 本身读不了会在此失败。
    try:
        os.chdir(vault)
    except OSError as e:
        print("cannot access vault: %s" % e, file=sys.stderr)
        sys.exit(1)
    if git(vault, ["rev-parse", "--is-inside-work-tree"]).strip() != "true":
        print("not a git repo: " + vault, file=sys.stderr)
        sys.exit(1)

    today = datetime.now().date()
    base = last_commit_before(vault, today.isoformat() + " 00:00:00")
    chars, files = added_chars(vault, base, "HEAD")
    week = compute_week(vault, today)

    payload = {
        "updated_ts": int(time.time()),
        "date": today.isoformat(),
        "chars": chars,
        "week": week,
        "files": dict(sorted(files.items(), key=lambda kv: -kv[1])),
    }
    # 主写：应用数据目录（无 TCC 限制）
    write_json(os.path.join(DATA_DIR, "daily-wordcount.json"), payload)
    # 次写：vault 附件（Obsidian 可直接读）；TCC 拦截时忽略
    try:
        write_json(os.path.join(vault, "附件", "daily-wordcount.json"), payload)
    except Exception:
        pass
    if "--print" in sys.argv:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
