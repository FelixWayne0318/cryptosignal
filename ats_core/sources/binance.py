# coding: utf-8
from __future__ import annotations

import os
import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from ats_core.backoff import sleep_retry

# Binance 期货 API 基础地址；可通过环境变量覆盖
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

# 统一默认的超时与重试次数（字符串也会被安全转成数字）
DEFAULT_TIMEOUT = _as_float(os.getenv("ATS_HTTP_TIMEOUT", os.getenv("HTTP_TIMEOUT", 5)), 5.0)
DEFAULT_RETRIES = _as_int(os.getenv("ATS_HTTP_MAX_RETRIES", os.getenv("HTTP_MAX_RETRIES", 4)), 4)

def _fetch(url: str,
           params: Dict[str, Any] | None = None,
           timeout: float | int | None = None,
           retries: int | None = None) -> Any:
    """
    GET 并解析 JSON；显式数值化 timeout/retries，避免类型错误。
    """
    to = DEFAULT_TIMEOUT if timeout is None else _as_float(timeout, DEFAULT_TIMEOUT)
    rt = DEFAULT_RETRIES if retries is None else _as_int(retries, DEFAULT_RETRIES)

    final_url = url
    if params:
        q = urllib.parse.urlencode(params, doseq=True)
        final_url = f"{url}?{q}"

    last_err: Exception | None = None
    for i in range(max(rt, 1)):
        try:
            req = urllib.request.Request(final_url, headers={"User-Agent": "ats-analyzer/1.0"})
            with urllib.request.urlopen(req, timeout=float(to)) as r:
                data = r.read()
            if not data:
                return None
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            last_err = e
            if i >= rt - 1:
                break
            # 退避重试（backoff 内部也只用数字参与计算）
            sleep_retry(i)
    if last_err:
        raise last_err

# ---------- 公共数据 ----------

def get_klines(symbol: str, interval: str = "1h", limit: int = 300) -> List[List[Any]]:
    """
    期货 K 线（原样返回 Binance 数组结构）
    GET /fapi/v1/klines
    """
    limit = _as_int(limit, 300)
    return _fetch(
        f"{BASE}/fapi/v1/klines",
        params={"symbol": symbol, "interval": interval, "limit": limit},
    )

def get_ticker_24h(symbol: str | None = None) -> Dict[str, Any] | List[Dict[str, Any]]:
    """
    24h 统计（含成交额等）
    GET /fapi/v1/ticker/24hr
    - 传入 symbol（如 "BTCUSDT"）返回单个 dict
    - 不传 / 传 None 返回全量 list[dict]
    """
    if symbol:
        return _fetch(f"{BASE}/fapi/v1/ticker/24hr", params={"symbol": symbol})
    else:
        # 不带 symbol 按 Binance 行为返回全市场列表
        return _fetch(f"{BASE}/fapi/v1/ticker/24hr", params=None)

# 兼容旧命名（有人从其他模块 import get_ticker_24hr）
get_ticker_24hr = get_ticker_24h

def get_funding_rate_hist(symbol: str,
                          startTime: int | None = None,
                          endTime: int | None = None,
                          limit: int = 1000) -> List[Dict[str, Any]]:
    """
    历史资金费率
    GET /fapi/v1/fundingRate
    """
    params: Dict[str, Any] = {"symbol": symbol, "limit": _as_int(limit, 1000)}
    if startTime is not None:
        params["startTime"] = _as_int(startTime, startTime)
    if endTime is not None:
        params["endTime"] = _as_int(endTime, endTime)
    return _fetch(f"{BASE}/fapi/v1/fundingRate", params=params)

# ---------- 指标数据：未成交合约量（Open Interest） ----------

def get_open_interest_hist(symbol: str,
                           period: str = "1h",
                           limit: int = 200) -> List[Dict[str, Any]]:
    """
    OI 历史
    GET /futures/data/openInterestHist
    period: 5m / 15m / 1h / 4h / 1d
    """
    limit = _as_int(limit, 200)
    return _fetch(
        f"{BASE}/futures/data/openInterestHist",
        params={"symbol": symbol, "period": period, "limit": limit}
    )