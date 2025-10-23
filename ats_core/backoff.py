# coding: utf-8
from __future__ import annotations
import os, time, random

def _as_float(x, default: float) -> float:
    try:
        return float(x)
    except Exception:
        return float(default)

# 允许通过环境变量覆盖，但一律强制转成 float
_BASE = _as_float(os.getenv("ATS_BACKOFF_BASE", os.getenv("BACKOFF_BASE", 1.0)), 1.0)
_MAX  = _as_float(os.getenv("ATS_BACKOFF_MAX",  os.getenv("BACKOFF_MAX",  10.0)), 10.0)

# 抖动区间（可选）
_JIT_LOW  = _as_float(os.getenv("ATS_BACKOFF_JITTER_LOW",  0.80), 0.80)
_JIT_HIGH = _as_float(os.getenv("ATS_BACKOFF_JITTER_HIGH", 1.20), 1.20)
if _JIT_LOW > _JIT_HIGH:
    _JIT_LOW, _JIT_HIGH = _JIT_HIGH, _JIT_LOW

def sleep_retry(i: int, base: float = _BASE, mx: float = _MAX) -> None:
    """指数退避 + 抖动，参数统一为 float，避免字符串导致的类型错误。"""
    try:
        i = int(i)
    except Exception:
        i = 0
    try:
        base = float(base)
    except Exception:
        base = _BASE
    try:
        mx = float(mx)
    except Exception:
        mx = _MAX

    backoff = min(mx, base * (2.0 ** float(i)))
    jitter  = random.uniform(_JIT_LOW, _JIT_HIGH)
    t = float(backoff) * float(jitter)
    # 给一个合理下限/上限，避免极端值
    if t < 0.05:
        t = 0.05
    if t > mx:
        t = mx
    time.sleep(t)