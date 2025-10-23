# coding: utf-8
from __future__ import annotations

from typing import Any, Dict, List, Callable

def _resolve_getter() -> Callable:
    """
    兼容两种命名：get_ticker_24h / get_ticker_24hr
    """
    try:
        from ats_core.sources.binance import get_ticker_24h as _fn
        return _fn
    except Exception:
        from ats_core.sources.binance import get_ticker_24hr as _fn
        return _fn

_get24h = _resolve_getter()

def _call_all() -> List[Dict[str, Any]]:
    """
    容错地调用“获取全量 24h”的方式。
    """
    # 优先传 None
    try:
        data = _get24h(None)
        if isinstance(data, list):
            return data
    except TypeError:
        pass
    # 退化为无参
    try:
        data = _get24h()
        if isinstance(data, list):
            return data
    except TypeError:
        pass
    # 最后尝试关键字
    data = _get24h(symbol=None)
    if not isinstance(data, list):
        raise TypeError("get_ticker_24h/all: expected list of dicts")
    return data

def _call_one(symbol: str) -> Dict[str, Any]:
    """
    容错地调用“获取单币 24h”的方式。
    """
    try:
        data = _get24h(symbol)
        if isinstance(data, dict):
            return data
    except TypeError:
        pass
    data = _get24h(symbol=symbol)
    if not isinstance(data, dict):
        raise TypeError("get_ticker_24h/one: expected dict")
    return data

# === 提供给上层使用的 API ===

def all_24h() -> List[Dict[str, Any]]:
    return _call_all()

def one_24h(symbol: str) -> Dict[str, Any]:
    return _call_one(symbol)