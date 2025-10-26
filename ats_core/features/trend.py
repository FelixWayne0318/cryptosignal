# coding: utf-8
"""
趋势维度（改进版）
- 使用软映射替代硬阈值
- 支持多空对称
- 返回 (T分数, Tm方向)
"""
from __future__ import annotations

from typing import List, Tuple, Iterable, Any
from .scoring_utils import directional_score

# -------------- 小工具：把"可能是列表"的值收敛成标量 ----------------

def _scalar(x: Any, default: float = 0.0) -> float:
    """
    把 x 收敛成 float：
    - 如果是数，直接转 float
    - 如果是 list/tuple：
        * 元素是数：取"平均值"
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

# -------------- 主函数：趋势打分（改进版：软映射 + 多空对称） ----------------

def score_trend(
    h: Iterable[float],
    l: Iterable[float],
    c: Iterable[float],
    c4: Iterable[float],   # 兼容旧签名；本实现未用到，但保留参数位置
    cfg: dict
) -> Tuple[int, int]:
    """
    返回 (T, Tm)（v2.0 对称版本）

    - T : -100~+100 趋势分
        * 正值：上升趋势 → 适合做多
        * 负值：下降趋势 → 适合做空
        * 0：震荡 → 中性
    - Tm: -1(空) / 0(震荡) / 1(多) - 市场实际趋势方向（保持不变）

    改进v2.0：
    1. ✅ 使用对称评分（-100到+100）
    2. ✅ 移除side_long参数
    3. ✅ 方向自包含
    4. ✅ Tm仍表示市场方向
    """
    H = [float(x) for x in h]
    L = [float(x) for x in l]
    C = [float(x) for x in c]
    if not C or len(C) < 30:
        return 0, 0  # 数据太短，给中性分（v2.0：±100系统中0为中性）

    # 参数配置
    ema_order_min_bars = int(cfg.get("ema_order_min_bars", 6))
    slope_lookback = int(cfg.get("slope_lookback", 12))
    atr_period = int(cfg.get("atr_period", 14))

    # 软映射参数
    slope_scale = float(cfg.get("slope_scale", 0.05))  # 斜率/ATR的标准差
    ema_bonus = float(cfg.get("ema_bonus", 15.0))  # EMA排列的加分
    r2_weight = float(cfg.get("r2_weight", 0.3))  # R²的权重

    # ========== 1. EMA 顺序（5/20） ==========
    ema5 = _ema(C, 5)
    ema20 = _ema(C, 20)
    k = min(ema_order_min_bars, len(C))
    ema_up = all(ema5[-i] > ema20[-i] for i in range(1, k + 1))
    ema_dn = all(ema5[-i] < ema20[-i] for i in range(1, k + 1))

    # ========== 2. 斜率/ATR 强度 ==========
    LB = min(max(5, slope_lookback), len(C))
    slope, r2 = _linreg_r2(C[-LB:])
    atr = _atr(H, L, C, atr_period)
    slope_per_bar = slope / max(1e-9, atr)

    # 判断市场实际趋势方向（Tm）
    if slope_per_bar > 0.02:
        dir_flag = 1  # 多头
    elif slope_per_bar < -0.02:
        dir_flag = -1  # 空头
    else:
        dir_flag = 0  # 震荡

    # ========== 3. 使用对称软映射计算分数 ==========
    # 导入对称评分函数
    from .scoring_utils import directional_score_symmetric

    # 斜率评分（正值=上涨，负值=下跌）
    slope_score = directional_score_symmetric(
        slope_per_bar,
        neutral=0.0,
        scale=slope_scale
    )  # -100 到 +100

    # ========== 4. EMA排列加分/减分 ==========
    if ema_up:
        # EMA多头排列 → 正分
        ema_score = ema_bonus
    elif ema_dn:
        # EMA空头排列 → 负分
        ema_score = -ema_bonus
    else:
        # 无排列 → 中性
        ema_score = 0

    # ========== 5. R² 置信度加权 ==========
    r2_val = _scalar(r2, 0.0)
    # R² 越高，趋势越清晰，给予加权
    confidence = r2_val  # 0-1之间

    # 基础分数
    T = slope_score * (1 - r2_weight) + ema_score

    # 如果R²高且方向一致，给予额外加分
    if dir_flag == 1 and ema_up:
        # 上涨趋势 + 多头排列 → 额外正分
        T += r2_weight * 50 * confidence
    elif dir_flag == -1 and ema_dn:
        # 下跌趋势 + 空头排列 → 额外负分
        T -= r2_weight * 50 * confidence
    elif dir_flag == 1:
        # 上涨趋势但EMA未排列 → 小额正分
        T += r2_weight * 25 * confidence
    elif dir_flag == -1:
        # 下跌趋势但EMA未排列 → 小额负分
        T -= r2_weight * 25 * confidence

    T = int(round(max(-100, min(100, T))))
    Tm = int(dir_flag)

    return T, Tm
