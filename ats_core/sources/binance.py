# coding: utf-8
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Union

from ats_core.backoff import sleep_retry  # 指数退避

# 允许通过环境变量覆盖网关，便于内网代理或将来切换
BASE = os.environ.get("BINANCE_FAPI_BASE", "https://fapi.binance.com")
SPOT_BASE = os.environ.get("BINANCE_SPOT_BASE", "https://api.binance.com")


def _get(
    path_or_url: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    timeout: float = 8.0,
    retries: int = 2,
) -> Any:
    """
    统一 GET 请求，带重试与简单 UA；path_or_url 可以是完整 URL 或以 / 开头的路径
    """
    if path_or_url.startswith("http"):
        url = path_or_url
    else:
        url = BASE + path_or_url
    q = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
    full = f"{url}?{q}" if q else url

    last_err: Optional[Exception] = None
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(full, headers={"User-Agent": "ats-analyzer/1.0"})
            with urllib.request.urlopen(req, timeout=float(timeout)) as r:
                data = r.read()
                return json.loads(data)
        except Exception as e:
            last_err = e
            sleep_retry(i)
    # 若仍失败，抛出最后一次的异常
    if last_err:
        raise last_err
    raise RuntimeError("unknown http error")


# ------------------------- K线 -------------------------

def get_klines(
    symbol: str,
    interval: str,
    limit: int = 300,
    start_time: Optional[Union[int, float]] = None,
    end_time: Optional[Union[int, float]] = None,
) -> List[list]:
    """
    返回符合 Binance /fapi/v1/klines 规范的二维数组
    每条记录字段：
      [ openTime, open, high, low, close, volume, closeTime, quoteAssetVolume,
        numberOfTrades, takerBuyBaseVolume, takerBuyQuoteVolume, ignore ]
    """
    symbol = symbol.upper()
    limit = int(max(1, min(int(limit), 1500)))
    params: Dict[str, Any] = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    # Binance 接受 ms 时间戳
    if start_time is not None:
        params["startTime"] = int(start_time)
    if end_time is not None:
        params["endTime"] = int(end_time)

    return _get("/fapi/v1/klines", params, timeout=10.0, retries=2)


def get_spot_klines(
    symbol: str,
    interval: str,
    limit: int = 300,
    start_time: Optional[Union[int, float]] = None,
    end_time: Optional[Union[int, float]] = None,
) -> List[list]:
    """
    获取现货K线数据（Binance Spot API）

    返回格式与合约相同：
      [ openTime, open, high, low, close, volume, closeTime, quoteAssetVolume,
        numberOfTrades, takerBuyBaseVolume, takerBuyQuoteVolume, ignore ]

    Args:
        symbol: 现货交易对（如 BTCUSDT）
        interval: K线周期（1m, 5m, 15m, 1h, 4h, 1d等）
        limit: 返回数量（最大1000）
        start_time: 开始时间（毫秒时间戳）
        end_time: 结束时间（毫秒时间戳）

    Returns:
        K线数据列表
    """
    symbol = symbol.upper()
    limit = int(max(1, min(int(limit), 1000)))
    params: Dict[str, Any] = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    if start_time is not None:
        params["startTime"] = int(start_time)
    if end_time is not None:
        params["endTime"] = int(end_time)

    # 使用现货API端点
    return _get(SPOT_BASE + "/api/v3/klines", params, timeout=10.0, retries=2)


# ------------------------- 未平仓量历史 -------------------------

def get_open_interest_hist(symbol: str, period: str = "1h", limit: int = 200) -> List[dict]:
    """
    /futures/data/openInterestHist
    返回形如：
      [{"symbol":"BTCUSDT","sumOpenInterest":"1234.5","sumOpenInterestValue":"...","timestamp":1690000000000}, ...]
    period: "5m"|"15m"|"30m"|"1h"|"2h"|"4h"|"6h"|"12h"|"1d"
    """
    symbol = symbol.upper()
    limit = int(max(1, min(int(limit), 500)))
    return _get(
        "/futures/data/openInterestHist",
        {"symbol": symbol, "period": period, "limit": limit},
        timeout=8.0,
        retries=2,
    )


# ------------------------- 资金费率历史（新增） -------------------------

def get_funding_hist(
    symbol: str,
    limit: int = 120,
    start_time: Optional[Union[int, float]] = None,
    end_time: Optional[Union[int, float]] = None,
) -> List[dict]:
    """
    /fapi/v1/fundingRate
    文档要点：
      - limit 最大 1000
      - startTime/endTime 为 ms
      - 返回字段包含 "fundingRate"、"fundingTime"
    """
    symbol = symbol.upper()
    limit = int(max(1, min(int(limit), 1000)))
    params: Dict[str, Any] = {"symbol": symbol, "limit": limit}
    if start_time is not None:
        params["startTime"] = int(start_time)
    if end_time is not None:
        params["endTime"] = int(end_time)
    rows = _get("/fapi/v1/fundingRate", params, timeout=8.0, retries=2)
    # 兼容返回为对象或数组（正常是数组）
    return list(rows) if isinstance(rows, list) else []


# ------------------------- 24h 统计 -------------------------

def get_ticker_24h(symbol: Optional[str] = None):
    """
    symbol=None -> 返回全市场列表；否则返回单个 symbol 的字典
    """
    params = {"symbol": symbol.upper()} if symbol else None
    return _get("/fapi/v1/ticker/24hr", params, timeout=8.0, retries=2)