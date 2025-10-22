# ats_core/features/open_interest.py
from statistics import median
from typing import Dict, Tuple, Any
from ats_core.sources.oi import fetch_oi_hourly, pct, pct_series

# 线性映射助手：把 x 从 [lo, hi] 线性映到 [0,1] 并截断
def _ramp(x: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 0.0
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))

def score_open_interest(symbol: str,
                        closes,
                        side_long: bool,
                        params: Dict[str, Any],
                        cvd6_fallback: float) -> Tuple[int, Dict[str, Any]]:
    """
    专注“变化率”的 OI 评分：
      - 主分量：oi24（按近 7 天中位数归一后的 24h 变化率）
      - 辅分量：价格↑/OI↑ 同向次数（up_up 或 dn_up，取决于方向）
      - 拥挤度：若当前 oi24 高于近 24h 变化率的 95 分位，扣分 crowding_penalty
    元数据返回：
      - oi1h_pct / oi24h_pct（百分比，保留两位）
      - upup12 / dnup12，同向计数
      - crowding_warn / p95_oi24（拥挤阈值）
      - den（归一化分母，中位数）
    """
    # 参数默认（缺键也不炸）
    default_par = {
        # 多头侧：希望 24h OI 上涨越多越好
        "long_oi24_lo":  1.0,   # 低于 1% 视为 0
        "long_oi24_hi":  8.0,   # 高于 8% 视为 1
        # 空头侧：希望 24h OI 下降（-oi24 越大越好）
        "short_oi24_lo": 2.0,   # -oi24 低于 2% 视为 0（oi24 > -2%）
        "short_oi24_hi": 10.0,  # -oi24 高于 10% 视为 1（oi24 < -10%）
        # 同向计数阈值（12 根内）
        "upup12_lo": 6,   # 6 次起才开始给分
        "upup12_hi": 12,  # 12 次封顶
        "dnup12_lo": 6,
        "dnup12_hi": 12,
        # 拥挤度
        "crowding_p95_penalty": 10,
        # 权重（总和不用正好=1，会在 0..100 内乘以 100）
        "w_change": 0.7,    # 变化率权重
        "w_align":  0.3,    # 价格-持仓同向权重
    }
    par = dict(default_par)
    if isinstance(params, dict):
        par.update(params)

    oi = fetch_oi_hourly(symbol, limit=200)
    # 兜底：数据不足用 CVD proxy，给一个温和的分数（避免全 0）
    if len(oi) < 30:
        O = int(100 * max(0.0, min(1.0, (cvd6_fallback - 0.01) / 0.05)))
        return O, {
            "oi1h_pct": None,
            "oi24h_pct": None,
            "dnup12":   None,
            "upup12":   None,
            "crowding_warn": False
        }

    den = median(oi[max(0, len(oi) - 168):])
    # 归一变化率
    oi1h = pct(oi[-1], oi[-2], den)
    oi24 = pct(oi[-1], oi[-25], den) if len(oi) >= 25 else 0.0

    # 最近 12 小时价格 vs OI 同向统计
    k = min(12, len(closes) - 1, len(oi) - 1)
    up_up = dn_up = 0
    for i in range(1, k + 1):
        dp = closes[-i] - closes[-i - 1]
        doi = oi[-i] - oi[-i - 1]
        if dp > 0 and doi > 0:
            up_up += 1
        if dp < 0 and doi > 0:
            dn_up += 1

    # 拥挤度：oi24 的历史分布（最近 look=24 的变化率序列）
    hist24 = pct_series(oi, 24)
    crowding_warn = False
    p95 = None
    if hist24:
        s = sorted(hist24)
        p95 = s[int(0.95 * (len(s) - 1))]
        crowding_warn = (oi24 >= p95)

    # —— 打分：主看“变化率”，辅看“同向” ——
    if side_long:
        s_change = _ramp(oi24, par["long_oi24_lo"], par["long_oi24_hi"])
        s_align  = _ramp(up_up, par["upup12_lo"], par["upup12_hi"])
    else:
        # 空头侧：-oi24 越大越好（即 oi24 越负越好）
        s_change = _ramp(-oi24, par["short_oi24_lo"], par["short_oi24_hi"])
        s_align  = _ramp(dn_up, par["dnup12_lo"], par["dnup12_hi"])

    O_raw = 100.0 * (par["w_change"] * s_change + par["w_align"] * s_align)

    # 拥挤度惩罚
    if crowding_warn:
        O_raw -= float(par["crowding_p95_penalty"])

    O = int(round(max(0.0, min(100.0, O_raw))))

    meta = {
        "oi1h_pct": round(oi1h * 100, 2),
        "oi24h_pct": round(oi24 * 100, 2),
        "dnup12": dn_up,
        "upup12": up_up,
        "crowding_warn": crowding_warn,
        "p95_oi24": round(p95 * 100, 2) if p95 is not None else None,
        "den": den,
    }
    return O, meta