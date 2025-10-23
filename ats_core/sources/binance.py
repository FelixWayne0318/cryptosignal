# coding: utf-8
from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request
import re
from typing import Any, Dict, Optional

from ats_core.cfg import CFG
from ats_core.backoff import sleep_retry

# ---- 工具：把 "500ms"/"2s"/"1m"/"10" 解析成秒 ----
_NUM_RE = re.compile(r'^\s*([0-9]*\.?[0-9]+)\s*([a-zA-Z%]*)\s*$')

def _to_seconds(x, default: float) -> float:
    if x is None:
        return float(default)
    try:
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str):
            m = _NUM_RE.match(x)
            if not m:
                return float(default)
            val = float(m.group(1))
            unit = (m.group(2) or '').lower()
            if unit in ('ms', 'millisecond', 'milliseconds'):
                return val / 1000.0
            if unit in ('m', 'min', 'mins', 'minute', 'minutes'):
                return val * 60.0
            # 默认按秒
            return val
    except Exception:
        return float(default)

def _to_int(x, default: int) -> int:
    try:
        return int(float(x))
    except Exception:
        return int(default)

# ---- 基础配置 ----
BASE: str = CFG.get("binance_base", default="https://fapi.binance.com")
_http = CFG.get("http", default={})
_http_backoff = CFG.get("http_backoff", default={})

UA = _http.get("user_agent") or "Mozilla/5.0 ATS/1.0 (+binance)"

DEF_TIMEOUT = _to_seconds(_http.get("timeout"), 10.0)
DEF_TRIES   = _to_int(_http_backoff.get("tries", 3), 3)
DEF_BBASE   = _to_seconds(_http_backoff.get("base", 0.5), 0.5)
DEF_BMAX    = _to_seconds(_http_backoff.get("max", 5.0), 5.0)

_ctx = ssl.create_default_context()

def _get(url: str,
         params: Dict[str, Any],
         *,
         timeout: Optional[float] = None,
         tries: Optional[int] = None,
         backoff_base: Optional[float] = None,
         backoff_max: Optional[float] = None) -> Any:
    """带指数回退与超时的 GET，并将响应 JSON 解析成 Python 对象。"""
    to = _to_seconds(timeout, DEF_TIMEOUT)
    tr = _to_int(tries, DEF_TRIES) if tries is not None else DEF_TRIES
    bbase = _to_seconds(backoff_base, DEF_BBASE) if backoff_base is not None else DEF_BBASE
    bmax  = _to_seconds(backoff_max,  DEF_BMAX)  if backoff_max  is not None else DEF_BMAX

    qs = urllib.parse.urlencode({k: str(v) for k, v in params.items()})
    full = f"{url}?{qs}"

    req = urllib.request.Request(full, headers={
        "User-Agent": UA,
        "Accept": "application/json,text/plain,*/*",
        "Connection": "close",
    })

    last_err: Optional[Exception] = None
    for i in range(tr):
        try:
            with urllib.request.urlopen(req, timeout=float(to), context=_ctx) as r:
                data = r.read()
                return json.loads(data.decode("utf-8"))
        except Exception as e:
            last_err = e
            # 最后一次失败就抛出，否则按回退策略重试
            if i >= tr - 1:
                break
            sleep_retry(i, base=bbase, mx=bmax)

    raise last_err  # type: ignore[misc]

def get_klines(symbol: str, interval: str, limit: int = 300):
    limit = _to_int(limit, 300)
    return _get(f"{BASE}/fapi/v1/klines", {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    })