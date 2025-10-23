#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Self Check for ATS Project
- 无需 curl/git；用 requests 做网络探测
- 自动定位项目根并设置 PYTHONPATH
- 检查：Python & requests & 项目包 -> DNS -> Binance HTTP -> 配置文件
- 可选：--send 测试 Telegram（需设置 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID）
退出码：0=通过；非0=存在失败
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from pathlib import Path
from typing import Optional

FAIL = 0
WARN = 0


def say(*a): print(*a)
def ok(msg): print(f"✅ {msg}")
def warn(msg):
    global WARN
    WARN += 1
    print(f"⚠️  {msg}")
def err(msg):
    global FAIL
    FAIL += 1
    print(f"❌ {msg}")


def project_root_from_here() -> Path:
    """假设文件位于 tools/self_check.py，项目根 = 父目录的父目录"""
    here = Path(__file__).resolve()
    # tools/ -> repo_root
    return here.parent.parent


def ensure_on_sys_path(p: Path):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)


def check_python_and_imports(repo_root: Path):
    say("------------------------------")
    say("[1/5] Python 基础与项目包")
    say(f"[ENV] REPO_ROOT={repo_root}")
    say(f"[ENV] PYTHONPATH.prepend={repo_root}")
    # 基础版本
    say(f"[PY] sys.version: {sys.version.split()[0]}")
    # requests
    try:
        import requests  # noqa
        ok("requests 可用")
    except Exception as e:
        err(f"requests 缺失：{e}")
        return
    # 项目包（根据你仓库结构，顶层包名可能是 ats）
    try:
        modname = os.environ.get("ATS_PKG", "ats")
        m = __import__(modname)
        path = getattr(m, "__file__", None)
        ok(f"import {modname} OK -> {path}")
    except Exception as e:
        # 不强制失败，但提醒
        warn(f"导入项目包失败（若你的代码不是以包方式组织可忽略）：{e}")


def check_dns():
    say("------------------------------")
    say("[2/5] DNS 解析")
    hosts = ["fapi.binance.com", "www.google.com", "1.1.1.1"]
    all_ok = True
    for h in hosts:
        try:
            ip = socket.gethostbyname(h)
            say(f"[DNS] {h} -> {ip}")
        except Exception as e:
            all_ok = False
            warn(f"[DNS] {h} 解析失败：{e}")
    if all_ok:
        ok("DNS 解析正常")
    else:
        err("存在 DNS 解析失败")


def try_get(session, url: str, timeout: float = 6.0) -> tuple[Optional[int], str]:
    try:
        r = session.get(url, timeout=timeout)
        return r.status_code, r.text[:200].replace("\n", " ")
    except Exception as e:
        return None, str(e)


def check_binance_http():
    say("------------------------------")
    say("[3/5] Binance HTTP 连通（requests）")
    try:
        import requests
    except Exception as e:
            err(f"requests 缺失：{e}")
            return
    s = requests.Session()
    s.headers.update({"User-Agent": "ats-selfcheck/1.0"})
    ok_all = True

    code, body = try_get(s, "https://fapi.binance.com/fapi/v1/ping")
    say(f"[HTTP] ping: {code if code is not None else 'ERR'} {('OK' if code == 200 else body)}")
    ok_all &= (code == 200)

    code, body = try_get(s, "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT")
    say(f"[HTTP] 24hr BTCUSDT: {code if code is not None else 'ERR'} {body}")
    ok_all &= (code == 200)

    if ok_all:
        ok("Binance HTTP 正常")
    else:
        err("Binance HTTP 存在失败")


def check_config(repo_root: Path):
    """
    同时兼容两种常见配置：
    - params.yml（你当前仓库已有）
    - config/params.json（另一套工程风格）
    """
    say("------------------------------")
    say("[4/5] 配置文件校验（params.yml / config/params.json）")

    yml = repo_root / "params.yml"
    jsn = repo_root / "config" / "params.json"

    loaded = None
    src = None
    fmt = None

    if yml.exists():
        try:
            import yaml  # PyYAML
        except Exception as e:
            warn(f"找到 {yml}，但未安装 PyYAML：{e}")
        else:
            with yml.open("r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
            src = yml
            fmt = "yaml"
    elif jsn.exists():
        with jsn.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
        src = jsn
        fmt = "json"

    if loaded is None:
        warn("未找到 params.yml 或 config/params.json（如配置在别处，可忽略此项）")
        return

    keys = list(loaded.keys()) if isinstance(loaded, dict) else []
    say(f"[CFG] 使用 {fmt}: {src}")
    say(f"[CFG] 顶层键数量: {len(keys)}")
    if len(keys) == 0:
        warn("配置为空？请确认内容是否正确")

    # 提示常见键，不强制
    hints = ["universe", "trend", "overlay", "limits"]
    miss = [h for h in hints if isinstance(loaded, dict) and h not in loaded]
    if miss:
        say(f"[CFG] 提示：未见常见键 -> {', '.join(miss)}")

    ok("配置文件可读取")


def maybe_send_telegram(args):
    """
    可选发送一条简单文本（需要 --send 并设置环境变量）：
    TELEGRAM_BOT_TOKEN   TELEGRAM_CHAT_ID（或 TELEGRAM_WATCH_CHAT_ID）
    """
    if not args.send:
        say("------------------------------")
        say("[5/5] Telegram 发送（默认跳过，仅提醒）")
        say("[TG] 使用 --send 才会尝试发送；并确保导出 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID")
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_WATCH_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        warn("未设置 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID，跳过发送")
        return

    try:
        import requests
    except Exception as e:
        warn(f"requests 缺失，无法发送：{e}")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"[ATS Self-Check] OK @ {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())}",
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=6)
        if r.ok and r.json().get("ok"):
            ok("Telegram 测试消息已发送")
        else:
            warn(f"Telegram 返回异常：{r.status_code} {r.text[:120]}")
    except Exception as e:
        warn(f"Telegram 发送失败：{e}")


def main():
    parser = argparse.ArgumentParser(
        description="ATS Self-Check（环境/网络/配置/可选Telegram）"
    )
    parser.add_argument("--send", action="store_true", help="尝试发送一条 Telegram 测试消息（需设置环境变量）")
    args = parser.parse_args()

    repo_root = project_root_from_here()
    ensure_on_sys_path(repo_root)

    say(f"=== ATS Self-Check @ {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC ===")

    check_python_and_imports(repo_root)
    check_dns()
    check_binance_http()
    check_config(repo_root)
    maybe_send_telegram(args)

    say("------------------------------")
    say(f"结果：WARN={WARN}  FAIL={FAIL}")
    if FAIL == 0:
        ok("Self-Check PASS")
        sys.exit(0)
    else:
        err("Self-Check FAIL")
        sys.exit(1)


if __name__ == "__main__":
    main()