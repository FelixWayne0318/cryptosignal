# coding: utf-8
from __future__ import annotations

from typing import Dict, List, Tuple

from ats_core.sources.klines import klines_15m, split_ohlcv

# 优先使用 ta_core 的指标；若不可用则提供极简兜底实现，避免线上报错
try:
    from ats_core.features.ta_core import ema as _ema, atr as _atr  # type: ignore
except Exception:  # pragma: no cover
    def _ema(arr: List[float], period: int) -> List[float]:
        out: List[float] = []
        k = 2.0 / (period + 1.0)
        s = None
        for x in arr:
            s = x if s is None else (x * k + s * (1 - k))
            out.append(float(s))
        return out

    def _atr(o: List[float], h: List[float], l: List[float], c: List[float], period: int = 14) -> List[float]:
        trs: List[float] = []
        prev_c = c[0] if c else 0.0
        for i in range(len(c)):
            tr = max(h[i] - l[i], abs(h[i] - prev_c), abs(l[i] - prev_c))
            trs.append(tr)
            prev_c = c[i]
        # 简单 EMA 平滑
        return _ema(trs, period)


def _cvd_from_v_tb(v: List[float], tb: List[float]) -> List[float]:
    """
    用 takerBuyBaseVolume 估 CVD：buy - sell = 2*tb - v
    """
    out: List[float] = []
    s = 0.0
    for i in range(min(len(v), len(tb))):
        s += (2.0 * tb[i] - v[i])
        out.append(s)
    return out


def _pivot_high_low(h: List[float], l: List[float], look: int) -> Tuple[float, float]:
    n = len(h)
    start = max(0, n - look)
    return max(h[start:]) if n else 0.0, min(l[start:]) if n else 0.0


_DEFAULTS: Dict[str, float] = {
    "ema10_side_window": 8,
    "ema10_side_min_ok": 6,
    "v3_over_v20_min": 0.8,
    "v3_over_v20_max": 2.2,
    "dV_abs_min": 0.05,
    "dV_abs_max": 0.8,
    "cvd_lookback": 5,
    "micro_pivot_look": 8,
    "micro_pivot_tolerance_atr1h": 0.25,
    "anti_explosion_atr15m_max": 2.5,   # ATR15m / ATR1h 上限
    "anti_explosion_vratio_max": 3.5,   # v3/v20 上限（极端放量否决）
}


def _p(params: Dict, key: str) -> float:
    return float(params.get(key, _DEFAULTS[key]))


def check_microconfirm_15m(symbol: str, side_long: bool, params: Dict, atr1h: float) -> Dict:
    """
    15m 级别的“微确认”
    返回：{"ok": bool, "flags": {...}, "veto": bool, "note": str}
    """
    rows = klines_15m(symbol, 200)
    if not rows:
        return {"ok": False, "flags": {}, "veto": True, "note": "no 15m data"}

    o, h, l, c, v, q, tb = split_ohlcv(rows)

    ema10 = _ema(c, 10)

    # 1) EMA10 同侧计数
    same_side = 0
    win = int(_p(params, "ema10_side_window"))
    for x in range(-win, 0):
        if x + len(c) <= 0:
            continue
        if side_long:
            same_side += int(c[x] >= ema10[x])
        else:
            same_side += int(c[x] <= ema10[x])
    ok_ema_side = same_side >= int(_p(params, "ema10_side_min_ok"))

    # 2) 微量能（v3/v20 与 dV_abs）
    v3 = sum(v[-3:]) / 3.0
    v20 = max(1e-12, sum(v[-20:]) / 20.0)
    vratio = v3 / v20
    dVabs = abs((v[-1] - v20) / v20)
    ok_vol = (
        _p(params, "v3_over_v20_min") <= vratio <= _p(params, "v3_over_v20_max")
        and _p(params, "dV_abs_min") <= dVabs <= _p(params, "dV_abs_max")
    )

    # 3) CVD 短斜率（近 L 根）
    L = int(_p(params, "cvd_lookback"))
    cv = _cvd_from_v_tb(v, tb)
    s = cv[-1] - cv[-L] if len(cv) > L else 0.0
    ok_cvd = (s > 0) if side_long else (s < 0)

    # 4) 微结构 pivot 未被破坏
    ph, pl = _pivot_high_low(h, l, int(_p(params, "micro_pivot_look")))
    tol = _p(params, "micro_pivot_tolerance_atr1h") * max(1e-12, float(atr1h))
    if side_long:
        ok_pivot = (l[-1] >= (pl - tol))
    else:
        ok_pivot = (h[-1] <= (ph + tol))

    # 5) 反爆量/反异常波动否决
    atr15 = _atr(o, h, l, c, 14)
    atr_ratio = (atr15[-1] / max(1e-12, float(atr1h))) if atr15 else 0.0
    veto = (atr_ratio > _p(params, "anti_explosion_atr15m_max")) or (vratio > _p(params, "anti_explosion_vratio_max"))

    # 可配置的最小通过条件数（默认2）
    min_pass = int(_p(params, "min_conditions_pass")) if "min_conditions_pass" in params else 2

    # 计算通过的条件数
    conditions_passed = sum([ok_ema_side, ok_vol, ok_cvd, ok_pivot])

    flags = {
        "ema10_side": ok_ema_side,
        "micro_vol": ok_vol,
        "cvd_slope": ok_cvd,
        "micro_pivot": ok_pivot,
        "vratio": round(vratio, 3),
        "atr15_over_atr1h": round(atr_ratio, 3),
        "conditions_passed": conditions_passed,
        "min_pass": min_pass
    }

    # 只要通过≥min_pass个条件，且不被veto，就算通过
    ok = (conditions_passed >= min_pass) and (not veto)

    note = ""
    if veto:
        note = "anti-explosion veto"
    elif not ok:
        note = f"only {conditions_passed}/4 conditions passed (need {min_pass})"
    else:
        note = f"{conditions_passed}/4 conditions passed"

    return {"ok": bool(ok), "flags": flags, "veto": bool(veto), "note": note}