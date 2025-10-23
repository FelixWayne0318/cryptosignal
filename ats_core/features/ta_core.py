# coding: utf-8
from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple
import math

try:
    import numpy as _np
except Exception:  # 极端环境兜底（但项目里一般都有 numpy）
    _np = None


# --------- 工具：把各种输入统一成 float 的 ndarray / list ---------

def _to_float_list(arr: Iterable) -> List[float]:
    out: List[float] = []
    for x in arr:
        try:
            # 常见情况：'108143.9' / '0' / None / '' 等
            out.append(float(x))
        except Exception:
            # 兜底：无法转换的给 0.0，避免整条链路报错中断
            out.append(0.0)
    return out


def _to_np(arr: Iterable) -> " _np.ndarray | List[float] ":
    """
    优先返回 numpy 数组；若 numpy 不可用则返回 float 列表。
    """
    fl = _to_float_list(arr)
    if _np is not None:
        return _np.asarray(fl, dtype=float)
    return fl


def _rolling_min(arr: Sequence[float], win: int) -> List[float]:
    n = len(arr)
    if win <= 0:
        return [min(arr)] * n if n else []
    out: List[float] = []
    cur: List[float] = []
    from collections import deque
    dq = deque()
    for i, v in enumerate(arr):
        # 维护一个单调队列（索引）
        while dq and dq[0] <= i - win:
            dq.popleft()
        while dq and arr[dq[-1]] >= v:
            dq.pop()
        dq.append(i)
        out.append(arr[dq[0]])
    return out


def _rolling_max(arr: Sequence[float], win: int) -> List[float]:
    n = len(arr)
    if win <= 0:
        return [max(arr)] * n if n else []
    out: List[float] = []
    from collections import deque
    dq = deque()
    for i, v in enumerate(arr):
        while dq and dq[0] <= i - win:
            dq.popleft()
        while dq and arr[dq[-1]] <= v:
            dq.pop()
        dq.append(i)
        out.append(arr[dq[0]])
    return out


# --------- 指标实现（全部做了数值化防御） ---------

def ema(arr: Iterable, n: int) -> List[float]:
    """
    指数移动平均（Wilder/Trading 常用定义）
    兼容字符串/列表/ndarray 输入；输出为 float 列表，长度与输入一致。
    """
    if n is None or n <= 0:
        # 退化：直接返回数值化后的序列
        return _to_float_list(arr)

    xs = _to_float_list(arr)
    if not xs:
        return []

    k = 2.0 / (float(n) + 1.0)
    out: List[float] = []
    s = xs[0]
    out.append(s)
    for i in range(1, len(xs)):
        x = xs[i]
        s = x * k + s * (1.0 - k)
        out.append(s)
    return out


def atr(h: Iterable, l: Iterable, c: Iterable, n: int = 14) -> List[float]:
    """
    Average True Range（Wilder）
    """
    hi = _to_float_list(h)
    lo = _to_float_list(l)
    cl = _to_float_list(c)

    m = min(len(hi), len(lo), len(cl))
    if m == 0:
        return []

    hi = hi[:m]
    lo = lo[:m]
    cl = cl[:m]

    trs: List[float] = []
    prev_close = cl[0]
    for i in range(m):
        tr = max(
            hi[i] - lo[i],
            abs(hi[i] - prev_close),
            abs(lo[i] - prev_close),
        )
        trs.append(tr)
        prev_close = cl[i]

    if n is None or n <= 1:
        return trs

    # Wilder 平滑：ATR_t = (ATR_{t-1}*(n-1) + TR_t)/n
    out: List[float] = []
    # 初值用前 n 个 TR 的简单均值（不足 n 就用已有长度）
    head = trs[: max(1, min(n, len(trs)))]
    s = sum(head) / float(len(head))
    out.extend([s] * len(head))  # 保持长度对齐

    for i in range(len(head), len(trs)):
        s = (s * (n - 1) + trs[i]) / float(n)
        out.append(s)
    return out


def chop14(h: Iterable, l: Iterable, c: Iterable) -> List[float]:
    """
    Choppiness Index（常用 14）
    定义：100 * log10( sum(TR, n) / (maxHigh_n - minLow_n) ) / log10(n)
    这里固定 n=14；若极端情况下分母<=0，则输出 100（极度震荡）
    """
    n = 14
    hi = _to_float_list(h)
    lo = _to_float_list(l)
    cl = _to_float_list(c)
    m = min(len(hi), len(lo), len(cl))
    if m == 0:
        return []
    hi, lo, cl = hi[:m], lo[:m], cl[:m]

    # 先算 TR
    trs: List[float] = []
    prev_close = cl[0]
    for i in range(m):
        tr = max(
            hi[i] - lo[i],
            abs(hi[i] - prev_close),
            abs(lo[i] - prev_close),
        )
        trs.append(tr)
        prev_close = cl[i]

    out: List[float] = []
    logn = math.log10(n)
    for i in range(m):
        if i + 1 < n:
            out.append(100.0)  # 样本不足时给高震荡
            continue
        s_tr = sum(trs[i - n + 1 : i + 1])
        max_h = max(hi[i - n + 1 : i + 1])
        min_l = min(lo[i - n + 1 : i + 1])
        denom = max_h - min_l
        if denom <= 0 or s_tr <= 0:
            out.append(100.0)
        else:
            out.append(100.0 * math.log10(s_tr / denom) / logn)
    return out


def rsq(y: Iterable, window: int) -> List[float]:
    """
    Rolling R^2：用简单线性回归的决定系数衡量趋势拟合度。
    """
    ys = _to_float_list(y)
    n = len(ys)
    if n == 0 or window is None or window <= 1:
        return [0.0] * n

    out: List[float] = []
    # 预先准备 x 序列：0..w-1
    xs = list(range(window))
    x_sum = sum(xs)
    x2_sum = sum([x * x for x in xs])
    denom_x = window * x2_sum - x_sum * x_sum
    if denom_x == 0:
        return [0.0] * n

    for i in range(n):
        if i + 1 < window:
            out.append(0.0)
            continue
        seg = ys[i - window + 1 : i + 1]
        y_sum = sum(seg)
        xy_sum = sum([xs[j] * seg[j] for j in range(window)])
        # 回归系数
        b = (window * xy_sum - x_sum * y_sum) / float(denom_x)
        a = (y_sum - b * x_sum) / float(window)
        # 拟合
        y_hat = [a + b * xs[j] for j in range(window)]
        # R^2
        y_avg = y_sum / float(window)
        ss_tot = sum([(seg[j] - y_avg) ** 2 for j in range(window)]) or 1e-12
        ss_res = sum([(seg[j] - y_hat[j]) ** 2 for j in range(window)])
        r2 = max(0.0, 1.0 - ss_res / ss_tot)
        out.append(r2)
    return out


def cvd(base_vol: Iterable, taker_buy_base: Iterable) -> List[float]:
    """
    Cumulative Volume Delta（以 baseVol / takerBuyBaseVol 近似）
    delta = 2 * taker_buy_base - base_vol
    """
    v = _to_float_list(base_vol)
    b = _to_float_list(taker_buy_base)
    m = min(len(v), len(b))
    if m == 0:
        return []
    v, b = v[:m], b[:m]
    out: List[float] = []
    s = 0.0
    for i in range(m):
        d = 2.0 * b[i] - v[i]
        s += d
        out.append(s)
    return out


def donchian(h: Iterable, l: Iterable, look: int) -> Tuple[List[float], List[float]]:
    """
    Donchian 通道（上轨=rolling max，高；下轨=rolling min，低）
    """
    hi = _to_float_list(h)
    lo = _to_float_list(l)
    m = min(len(hi), len(lo))
    if m == 0:
        return [], []
    hi, lo = hi[:m], lo[:m]
    upper = _rolling_max(hi, look)
    lower = _rolling_min(lo, look)
    return upper, lower