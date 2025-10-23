# coding: utf-8
from __future__ import annotations

from typing import Any, Dict, List
from ats_core.sources.binance import get_ticker_24h

def all_24h() -> List[Dict[str, Any]]:
    xs = get_ticker_24h(None)
    return xs if isinstance(xs, list) else []

def one_24h(symbol: str) -> Dict[str, Any]:
    x = get_ticker_24h(symbol)
    return x if isinstance(x, dict) else {}