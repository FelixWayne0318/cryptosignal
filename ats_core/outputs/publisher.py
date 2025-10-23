# coding: utf-8
from __future__ import annotations

import json
import os
import urllib.request
from typing import Optional

"""
Telegram 发送（UTF-8 / JSON POST）
- 解决中文/Emoji 发送时的 ascii 编码报错
- 支持覆盖 chat_id；否则从环境变量兜底
  TELEGRAM_WATCH_CHAT_ID / TELEGRAM_TRADE_CHAT_ID / TELEGRAM_CHAT_ID / ATS_TELEGRAM_CHAT_ID
"""

def _env(key: str) -> str:
    v = os.getenv(key)
    return v if v is not None else ""

def _pick_chat_id(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    # 一般从调用方传入；否则兜底
    return (_env("TELEGRAM_CHAT_ID") or _env("ATS_TELEGRAM_CHAT_ID"))

def telegram_send(text: str, chat_id: Optional[str] = None, parse_mode: str = "HTML") -> None:
    token = (_env("TELEGRAM_BOT_TOKEN") or _env("ATS_TELEGRAM_BOT_TOKEN")).strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN 未设置")

    chat = _pick_chat_id(chat_id).strip()
    if not chat:
        raise RuntimeError("未提供 chat_id 且未配置 TELEGRAM_CHAT_ID/ATS_TELEGRAM_CHAT_ID")

    api = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Accept": "application/json",
    }

    req = urllib.request.Request(api, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        # 简单校验响应；失败会抛异常被上层捕获
        _ = r.read()