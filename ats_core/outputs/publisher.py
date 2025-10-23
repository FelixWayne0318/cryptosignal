# coding: utf-8
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Optional

def _env(name: str, default: Optional[str]=None) -> Optional[str]:
    import os
    return os.getenv(name, default)

def telegram_send(text: str,
                  chat_id: Optional[str] = None,
                  bot_token: Optional[str] = None) -> None:
    """
    发送纯文本到 Telegram。支持在调用时覆盖 chat_id / bot_token。
    回退顺序：
      - 入参 chat_id / bot_token
      - 环境变量 TELEGRAM_CHAT_ID / TELEGRAM_BOT_TOKEN
      - 兼容旧名 ATS_TELEGRAM_CHAT_ID / ATS_TELEGRAM_BOT_TOKEN
    """
    chat_id = (chat_id
               or _env("TELEGRAM_CHAT_ID")
               or _env("ATS_TELEGRAM_CHAT_ID"))
    bot_token = (bot_token
                 or _env("TELEGRAM_BOT_TOKEN")
                 or _env("ATS_TELEGRAM_BOT_TOKEN"))
    if not bot_token or not chat_id:
        raise RuntimeError("telegram_send 缺少 bot_token 或 chat_id")

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    body = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/x-www-form-urlencoded"
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        _ = json.loads(r.read().decode("utf-8"))