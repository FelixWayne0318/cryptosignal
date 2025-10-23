# coding: utf-8
from __future__ import annotations

import random
import time
import re
from typing import Tuple

# 解析 "500ms" / "2s" / "1m" / "10" 为秒
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

def next_delay(i: int, base=0.5, mx=5.0, jitter: Tuple[float, float] = (0.8, 1.2)) -> float:
    """计算第 i 次重试的等待时间（秒），指数回退 + 抖动。"""
    i = int(i) if i is not None else 0
    b = _to_seconds(base, 0.5)
    M = _to_seconds(mx, 5.0)
    lo, hi = jitter
    if not (isinstance(lo, (int, float)) and isinstance(hi, (int, float)) and hi >= lo and lo > 0):
        lo, hi = 0.8, 1.2
    d = min(M, b * (2 ** i))
    return float(d) * (lo + (hi - lo) * random.random())

def sleep_retry(i: int, base=0.5, mx=5.0, jitter: Tuple[float, float] = (0.8, 1.2)) -> None:
    """按指数回退策略 sleep 一段时间。"""
    time.sleep(next_delay(i, base=base, mx=mx, jitter=jitter))