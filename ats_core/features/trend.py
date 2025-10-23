# coding: utf-8
from __future__ import annotations

from typing import List, Tuple, Iterable, Any

# -------------- 小工具：把“可能是列表”的值收敛成标量 ----------------

def _scalar(x: Any, default: float = 0.0) -> float:
    """
    把 x 收敛成 float：
    - 如果是数，直接转 float
    - 如果是 list/tuple：
        * 元素是数：取“平均值”
        * 元素是二元组（如 (slope, r2)）：优先取第 2 项（r2），否则取第 1 项
        * 其它结构：忽略
      最终对收集到的数取平均值；若收集不到，返回 default
    """
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, (list, tuple)):
        buf: List[float] = []
        for y in x:
            if isinstance(y, (int, float)):
                buf.append(float(y))
            elif isinstance(y, (list, tuple)) and len(y) > 0:
                cand = None
                if len(y) >= 2 and isinstance(y[1], (int, float)):
                    cand = float(y[1])
                elif isinstance(y[0], (int, float)):
                    cand = float(y[0])
                if cand is not None:
                    buf.append(cand)
        if buf:
            return sum(buf) / len(buf)
    return float(default)

# -------------- 指标计算（纯 Python，无第三方依赖） ----------------

def _ema(xs: List[float], period: int) -> List[float]:
    n = int(period)
    if n <= 1 or len(xs) == 0:
        return [xs[-1]] * len(xs) if xs else []
    alpha = 2.0 / (n + 1.0)
    out: List[float] = []
    ema = xs[0]
    out.append(ema)
    for i in range(1, len(xs)):
        ema = alpha * xs[i] + (1 - alpha) * ema
        out.append(ema)
    return out

def _atr(h: List[float], l: List[float], c: List[float], period: int) -> float:
    n = max(1, int(period))
    if len(c) < 2:
        return 1.0
    trs: List[float] = []
    prev_close = c[0]
    for i in range(1, len(c)):
        tr = max(h[i] - l[i], abs(h[i] - prev_close), abs(l[i] - prev_close))
        trs.append(tr)
        prev_close = c[i]
    if not trs:
        return 1.0
    if len(trs) < n:
        return max(1e-9, sum(trs) / len(trs))
    return max(1e-9, sum(trs[-n:]) / n)

def _linreg_r2(y: List[float]) -> Tuple[float, float]:
    """
    对 y 与索引做简单一元线性回归，返回 (slope, r^2)
    """
    n = len(y)
    if n <= 1:
        return 0.0, 0.0
    xs = list(range(n))
    mean_x = (n - 1) / 2.0
    mean_y = sum(y) / n
    num = sum((xs[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    den = sum((xs[i] - mean_x) ** 2 for i in range(n))
    slope = num / den if den != 0 else 0.0
    ss_tot = sum((yy - mean_y) ** 2 for yy in y)
    ss_res = sum((y[i] - (slope * xs[i] + (mean_y - slope * mean_x))) ** 2 for i in range(n))
    r2 = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
    if not (r2 == r2):  # NaN
        r2 = 0.0
    r2 = max(0.0, min(1.0, r2))
    return slope, r2

# -------------- 主函数：趋势打分 ----------------

def score_trend(
    h: Iterable[float],
    l: Iterable[float],
    c: Iterable[float],
    c4: Iterable[float],   # 兼容旧签名；本实现未用到，但保留参数位置
    cfg: dict
) -> Tuple[int, int]:
    """
    返回 (T, Tm)
    - T : 0~100 趋势分
    - Tm: -1(空) / 0(震荡) / 1(多)
    """
    H = [float(x) for x in h]
    L = [float(x) for x in l]
    C = [float(x) for x in c]
    if not C or len(C) < 30:
        return 50, 0  # 数据太短，给中性分

    # 与 params.json 对齐的键位（有默认）
    ema_order_min_bars = int(cfg.get("ema_order_min_bars", 6))
    slope_atr_min_long = float(cfg.get("slope_atr_min_long", 0.06))
    slope_atr_min_short = float(cfg.get("slope_atr_min_short", 0.04))
    slope_lookback = int(cfg.get("slope_lookback", 12))
    atr_period = int(cfg.get("atr_period", 14))

    # 1) EMA 顺序（5/20）
    ema5 = _ema(C, 5)
    ema20 = _ema(C, 20)
    k = min(ema_order_min_bars, len(C))
    ema_up = all(ema5[-i] > ema20[-i] for i in range(1, k + 1))
    ema_dn = all(ema5[-i] < ema20[-i] for i in range(1, k + 1))

    T = 50
    if ema_up:
        T += 15
    elif ema_dn:
        T -= 15

    # 2) 斜率/ATR 强度
    LB = min(max(5, slope_lookback), len(C))
    slope, r2 = _linreg_r2(C[-LB:])
    atr = _atr(H, L, C, atr_period)
    slope_per_bar = slope / max(1e-9, atr)

    if slope_per_bar >= slope_atr_min_long:
        T += 25; dir_flag = 1
    elif slope_per_bar <= -slope_atr_min_long:
        T -= 25; dir_flag = -1
    elif slope_per_bar >= slope_atr_min_short:
        T += 12; dir_flag = 1
    elif slope_per_bar <= -slope_atr_min_short:
        T -= 12; dir_flag = -1
    else:
        dir_flag = 0

    # 3) R² 置信度（兼容 list/tuple）
    r2_val = _scalar(r2, 0.0)
    boost = 40.0 * max(0.0, min(1.0, (r2_val - 0.45) / 0.25))
    if dir_flag == 1 and ema_up:
        T += int(boost)
    elif dir_flag == -1 and ema_dn:
        T += int(boost)
    else:
        T += int(0.5 * boost)

    T = int(max(0, min(100, T)))
    Tm = int(dir_flag)
    return T, Tm