# coding: utf-8
"""
Open Interest feature scoring

修复点：
- OI 数据不足（len(oi) < 30）时，不再把缺失当成“0 分”。
  默认采用平滑的回退打分（基于 cvd6_fallback），避免误导性的 0。
  若希望严格以“缺失”为 None，可将环境变量 ATS_OI_STRICT_NONE=1。

- 正常路径保留你原有的映射逻辑，并对异常做了保护，确保输出在 0~100。
"""

from typing import Tuple, Optional, Dict, Any
from statistics import median
from ats_core.sources.oi import fetch_oi_hourly, pct, pct_series

# 可通过环境变量切换“严格缺失为 None”模式（默认为 False）
import os
STRICT_NONE_IF_INSUFFICIENT = os.getenv("ATS_OI_STRICT_NONE", "0") in ("1", "true", "TRUE")

def _percentile(xs, p: float) -> float:
    """简易 percentile（无 numpy 依赖），p ∈ [0,1]"""
    if not xs:
        return float("nan")
    q = sorted(xs)
    i = int(round((len(q) - 1) * max(0.0, min(1.0, p))))
    return q[i]

def _fallback_from_cvd6(cvd6_fallback: Optional[float]) -> int:
    """
    将 cvd6_fallback 平滑映射为 0~100 的得分。
    - 若 cvd6 ∈ [-1, 1]（常见相关/标准化因子），映射到 10~90，居中 50；
    - 若 cvd6 ∈ [0, 1]，按 0~100 映射；
    - 其它数值做裁剪后再映射；若 None，给出中性 50。
    """
    if cvd6_fallback is None:
        return 50
    try:
        x = float(cvd6_fallback)
    except Exception:
        return 50

    if -1.0 <= x <= 1.0:
        # 以 50 为中性，±1 → ±40 的摆幅，留出安全边界
        s = 0.5 + 0.4 * x
    elif 0.0 <= x <= 1.0:
        s = x
    else:
        # 粗暴裁剪再居中
        s = max(0.0, min(1.0, x))
    return int(round(100.0 * max(0.0, min(1.0, s))))

def score_open_interest(symbol: str,
                        closes,
                        side_long: bool,
                        params: Dict[str, Any],
                        cvd6_fallback: Optional[float]
                        ) -> Tuple[Optional[int], Dict[str, Any]]:
    """
    返回 (O, meta)
      - O: 0~100 的整数；若数据不足且启用严格模式则为 None
      - meta: 诊断信息（oi1h_pct/oi24h_pct/dnup12/upup12/crowding_warn）
    """
    oi = fetch_oi_hourly(symbol, limit=200)
    if not isinstance(oi, (list, tuple)):
        oi = []

    # —— 数据不足：平滑回退或严格缺失 —— #
    if len(oi) < 30:
        meta = {
            "oi1h_pct": None,
            "oi24h_pct": None,
            "dnup12": None,
            "upup12": None,
            "crowding_warn": False,
            "reason": "oi_insufficient",
        }
        if STRICT_NONE_IF_INSUFFICIENT:
            return None, meta
        # 默认给一个“中性且不误导”的回退分（避免长期显示 0）
        O = _fallback_from_cvd6(cvd6_fallback)
        return O, meta

    # —— 正常路径 —— #
    # 归一化分母：近 168 小时（1 周）的中位数，避免极端值/除 0
    try:
        den = median(oi[max(0, len(oi) - 168):])
        den = den if den not in (None, 0.0) else 1e-12
    except Exception:
        den = 1e-12

    # 短/中期相对变化（相对 den）
    try:
        oi1h = pct(oi[-1], oi[-2], den)
    except Exception:
        oi1h = 0.0
    oi24 = 0.0
    try:
        if len(oi) >= 25:
            oi24 = pct(oi[-1], oi[-25], den)
    except Exception:
        oi24 = 0.0

    # 近 12 根“价格方向 vs OI 方向”统计
    k = max(0, min(12, len(closes) - 1, len(oi) - 1))
    up_up = 0
    dn_up = 0
    for i in range(1, k + 1):
        dp  = closes[-i] - closes[-i - 1]
        doi = oi[-i]     - oi[-i - 1]
        if dp > 0 and doi > 0:
            up_up += 1
        if dp < 0 and doi > 0:
            dn_up += 1

    # 拥挤度：用 24h 变化的 95 分位做阈值
    hist24 = []
    try:
        hist24 = pct_series(oi, 24)
    except Exception:
        hist24 = []
    p95 = _percentile(hist24, 0.95) if len(hist24) >= 10 else float("inf")
    crowd_warn = (oi24 >= p95)

    # --- 打分映射（保留你的原始逻辑，但做保护） --- #
    try:
        if side_long:
            s1 = (oi24 - params["long_oi24_lo"]) / (params["long_oi24_hi"] - params["long_oi24_lo"])
            s1 = max(0.0, min(1.0, float(s1)))
            s2 = (up_up - 6) / (12 - 6) if 12 > 6 else 0.0
            s2 = max(0.0, min(1.0, float(s2)))
            O = int(round(80 * s1 + 20 * s2))
        else:
            a = (dn_up - params["short_dnup12_lo"]) / (params["short_dnup12_hi"] - params["short_dnup12_lo"])
            a = max(0.0, min(1.0, float(a)))
            b = ((-oi24) - (-params["short_oi24_hi"])) / ((-params["short_oi24_lo"]) - (-params["short_oi24_hi"]))
            b = max(0.0, min(1.0, float(b)))
            O = int(round(100 * max(a, b)))
    except Exception:
        # 参数缺失时，退回到仅由 oi24 方向给个保守分
        base = oi24 if side_long else (-oi24)
        # 将 base 粗略压缩到 [0,1]
        s = max(0.0, min(1.0, 0.5 + 0.5 * base))
        O = int(round(100 * s))

    # 拥挤扣分
    try:
        pen = int(params.get("crowding_p95_penalty", 0))
    except Exception:
        pen = 0
    if crowd_warn and pen > 0:
        O = max(0, O - pen)

    # 裁剪到 0~100
    O = max(0, min(100, int(O)))

    meta = {
        "oi1h_pct": round(oi1h * 100, 2),
        "oi24h_pct": round(oi24 * 100, 2),
        "dnup12": dn_up,
        "upup12": up_up,
        "crowding_warn": crowd_warn,
    }
    return O, meta