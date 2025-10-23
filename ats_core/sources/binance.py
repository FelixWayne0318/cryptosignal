# coding: utf-8
from __future__ import annotations
import os, json, urllib.parse, urllib.request
from typing import Any, Dict, List, Tuple
from ats_core.backoff import sleep_retry

BASE = os.getenv("ATS_BINANCE_BASE", "https://fapi.binance.com")

def _as_float(x, default: float) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)

def _as_int(x, default: int) -> int:
    try:
        return int(float(x))
    except Exception:
        return int(default)

# 全局默认：强制为正确类型
DEFAULT_TIMEOUT = _as_float(os.getenv("ATS_HTTP_TIMEOUT", os.getenv("HTTP_TIMEOUT", 5)), 5.0)
DEFAULT_RETRIES = _as_int(os.getenv("ATS_HTTP_MAX_RETRIES", os.getenv("HTTP_MAX_RETRIES", 4)), 4)

def _fetch(url: str, params: Dict[str, Any] | None = None,
           timeout: float | int | None = None, retries: int | None = None) -> Any:
    """GET 并解析 JSON。timeout/retries 一律显式转型。"""
    to = DEFAULT_TIMEOUT if timeout is None else _as_float(timeout, DEFAULT_TIMEOUT)
    rt = DEFAULT_RETRIES if retries is None else _as_int(retries, DEFAULT_RETRIES)

    if params:
        q = urllib.parse.urlencode(params, doseq=True)
        url = f"{url}?{q}"

    for i in range(max(rt, 1)):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ats-analyzer/1.0"})
            with urllib.request.urlopen(req, timeout=float(to)) as r:
                data = r.read()
            # 统一 JSON 解析
            if not data:
                return None
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            if i >= rt - 1:
                # 最后一次仍失败，抛出
                raise
            sleep_retry(i)

def get_klines(symbol: str, interval: str = "1h", limit: int = 300) -> List[List[Any]]:
    """返回原生 kline 数组（与 binance API 兼容），由上层做转换。"""
    limit = _as_int(limit, 300)
    return _fetch(
        f"{BASE}/fapi/v1/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
    )

# 如果你有其他数据源函数（OI/资金费/现货等），沿用 _fetch 即可，注意把 timeout/retries 传为数字或留空。