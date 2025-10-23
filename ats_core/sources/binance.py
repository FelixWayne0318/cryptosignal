# coding: utf-8
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from ats_core.backoff import sleep_retry  # 你的仓库里已有

BASE = "https://fapi.binance.com"

def _get(url: str, params: Optional[Dict[str, Any]] = None, timeout: float = 8.0, retries: int = 2):
    q = urllib.parse.urlencode(params or {})
    full = f"{url}?{q}" if q else url
    last_err = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": "ats-analyzer/1.0"})
            # timeout 必须是数字，不能是字符串
            with urllib.request.urlopen(req, timeout=float(timeout)) as r:
                data = r.read()
                return json.loads(data)
        except Exception as e:
            last_err = e
            sleep_retry(i)  # 指数退避
    raise last_err if last_err else RuntimeError("unknown http error")

# ------------------------- K线 -------------------------

def get_klines(symbol: str, interval: str, limit: int = 300) -> List[List[Any]]:
    return _get(
        BASE + "/fapi/v1/klines",
        {"symbol": symbol, "interval": interval, "limit": int(limit)},
        timeout=8.0,
        retries=2,
    )

# ------------------------- 未平仓量历史 -------------------------

def get_open_interest_hist(symbol: str, period: str = "1h", limit: int = 30) -> List[Dict[str, Any]]:
    """
    返回列表，每项为字典，包含：
    ['symbol','sumOpenInterest','sumOpenInterestValue','CMCCirculatingSupply','timestamp']
    """
    return _get(
        BASE + "/futures/data/openInterestHist",
        {"symbol": symbol, "period": period, "limit": int(limit)},
        timeout=8.0,
        retries=2,
    )

# ------------------------- 24h 统计 -------------------------

def get_ticker_24h(symbol: Optional[str] = None):
    """
    symbol=None -> 返回全市场列表；否则返回单个 symbol 的字典
    """
    params = {"symbol": symbol} if symbol else None
    return _get(BASE + "/fapi/v1/ticker/24hr", params, timeout=8.0, retries=2)