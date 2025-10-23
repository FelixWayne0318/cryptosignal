# coding: utf-8
from __future__ import annotations

import os
import json
import mimetypes
import urllib.request
import urllib.parse
import uuid
from typing import Any, Dict, Optional, Tuple, Union

# -----------------------
# 环境变量解析
# -----------------------
def _get_token() -> str:
    # 兼容旧/新变量名
    for k in ("TELEGRAM_BOT_TOKEN", "ATS_TELEGRAM_BOT_TOKEN"):
        v = os.getenv(k)
        if v:
            return v.strip()
    raise RuntimeError("TELEGRAM_BOT_TOKEN 未设置")

def _resolve_chat_id(target: Optional[str] = None) -> str:
    """
    target 可为: 'trade' | 'watch' | 'base' | None
    优先级:
      trade  -> TELEGRAM_TRADE_CHAT_ID -> TELEGRAM_CHAT_ID
      watch  -> TELEGRAM_WATCH_CHAT_ID -> TELEGRAM_CHAT_ID
      base   -> TELEGRAM_CHAT_ID
      None   -> TELEGRAM_CHAT_ID
    """
    t = (target or "").lower()
    if t == "trade":
        return os.getenv("TELEGRAM_TRADE_CHAT_ID") \
            or os.getenv("TELEGRAM_CHAT_ID") \
            or ""
    if t == "watch":
        return os.getenv("TELEGRAM_WATCH_CHAT_ID") \
            or os.getenv("TELEGRAM_CHAT_ID") \
            or ""
    if t == "base":
        return os.getenv("TELEGRAM_CHAT_ID") or ""
    # 默认
    return os.getenv("TELEGRAM_CHAT_ID") or ""

def _api_url(method: str) -> str:
    token = _get_token()
    return f"https://api.telegram.org/bot{token}/{method}"

# -----------------------
# 发送文本（UTF-8 POST）
# -----------------------
def telegram_send(
    text: str,
    chat_id: Optional[str] = None,
    parse_mode: Optional[str] = "HTML",
    disable_web_page_preview: bool = True,
    disable_notification: bool = False,
    protect_content: bool = False,
    target: Optional[str] = None,
) -> Dict[str, Any]:
    """
    发送纯文本消息（POST, UTF-8, 不再拼接中文到 URL）
    - chat_id 为空时按 target/环境变量解析
    - parse_mode: "HTML" / "MarkdownV2" / None
    """
    cid = (chat_id or _resolve_chat_id(target)).strip()
    if not cid:
        raise RuntimeError("没有可用的 chat_id（请设置 TELEGRAM_CHAT_ID 或对应 *WATCH/TRADE_CHAT_ID）")

    payload = {
        "chat_id": cid,
        "text": text,
        "disable_web_page_preview": "true" if disable_web_page_preview else "false",
        "disable_notification": "true" if disable_notification else "false",
        "protect_content": "true" if protect_content else "false",
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    data = urllib.parse.urlencode(payload, doseq=True, encoding="utf-8").encode("utf-8")
    req = urllib.request.Request(
        _api_url("sendMessage"),
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        body = resp.read()
        try:
            return json.loads(body.decode("utf-8", errors="replace"))
        except Exception:
            return {"ok": False, "raw": body}

# -----------------------
# 发送文件（文档）
# -----------------------
def _encode_multipart(fields: Dict[str, str], files: Dict[str, Tuple[str, bytes, str]]) -> Tuple[bytes, str]:
    """
    fields: 普通表单字段
    files:  { field_name: (filename, content_bytes, mime) }
    """
    boundary = uuid.uuid4().hex
    boundary_bytes = boundary.encode()
    lines = []

    def _part_header(name: str, filename: Optional[str] = None, content_type: Optional[str] = None) -> bytes:
        disp = f'form-data; name="{name}"'
        if filename:
            disp += f'; filename="{filename}"'
        hdrs = [f"Content-Disposition: {disp}"]
        if content_type:
            hdrs.append(f"Content-Type: {content_type}")
        return ("\r\n".join(hdrs) + "\r\n\r\n").encode("utf-8")

    # text fields
    for k, v in (fields or {}).items():
        lines.append(b"--" + boundary_bytes + b"\r\n")
        lines.append(_part_header(k))
        lines.append(v.encode("utf-8") if isinstance(v, str) else str(v).encode("utf-8"))
        lines.append(b"\r\n")

    # file fields
    for name, (filename, content, mime) in (files or {}).items():
        lines.append(b"--" + boundary_bytes + b"\r\n")
        lines.append(_part_header(name, filename=filename, content_type=mime or "application/octet-stream"))
        lines.append(content)
        lines.append(b"\r\n")

    # end
    lines.append(b"--" + boundary_bytes + b"--\r\n")
    body = b"".join(lines)
    ctype = f"multipart/form-data; boundary={boundary}"
    return body, ctype

def telegram_send_document(
    file_path: str,
    caption: Optional[str] = None,
    chat_id: Optional[str] = None,
    parse_mode: Optional[str] = "HTML",
    target: Optional[str] = None,
) -> Dict[str, Any]:
    """
    发送文档（如 .tgz/.zip/.csv 等）
    """
    cid = (chat_id or _resolve_chat_id(target)).strip()
    if not cid:
        raise RuntimeError("没有可用的 chat_id（请设置 TELEGRAM_CHAT_ID 或对应 *WATCH/TRADE_CHAT_ID）")

    with open(file_path, "rb") as f:
        content = f.read()

    filename = os.path.basename(file_path)
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    fields = {"chat_id": cid}
    if caption:
        fields["caption"] = caption
    if parse_mode:
        fields["parse_mode"] = parse_mode

    body, ctype = _encode_multipart(fields, {"document": (filename, content, mime)})

    req = urllib.request.Request(
        _api_url("sendDocument"),
        data=body,
        headers={"Content-Type": ctype},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
        try:
            return json.loads(raw.decode("utf-8", errors="replace"))
        except Exception:
            return {"ok": False, "raw": raw}