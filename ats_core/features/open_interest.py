# ats_core/features/open_interest.py
"""
O（持仓）评分 - 使用方向性软映射

改进：
- 旧版：oi24 < 1% → 0 分（硬阈值）
- 新版：oi24 = 0.5% → 约 42 分，1.5% → 约 57 分（软映射）
"""
from statistics import median
from typing import Dict, Tuple, Any
from ats_core.sources.oi import fetch_oi_hourly, pct, pct_series
from ats_core.features.scoring_utils import directional_score

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
    # 参数默认
    default_par = {
        "oi24_scale": 3.0,          # OI 24h变化率缩放系数（3% 给约 69 分）
        "align_scale": 4.0,          # 同向次数缩放系数（4次 给约 69 分）
        "oi_weight": 0.7,            # OI 变化率权重
        "align_weight": 0.3,         # 同向权重
        "crowding_p95_penalty": 10,  # 拥挤度惩罚
        "min_oi_samples": 30,        # 最少 OI 数据点
    }
    par = dict(default_par)
    if isinstance(params, dict):
        par.update(params)

    oi = fetch_oi_hourly(symbol, limit=200)
    # 兜底：数据不足时使用 CVD proxy
    if len(oi) < par["min_oi_samples"]:
        O = directional_score(
            cvd6_fallback,
            neutral=0.0,
            scale=0.02,
            max_bonus=40  # 降低最大值，因为 CVD 不如 OI 准确
        )
        return O, {
            "oi1h_pct": None,
            "oi24h_pct": None,
            "dnup12":   None,
            "upup12":   None,
            "crowding_warn": False,
            "data_source": "cvd_fallback"
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

    # —— 打分：使用软映射 ——
    if side_long:
        # 做多：希望 OI 上升
        oi_score = directional_score(oi24, neutral=0.0, scale=par["oi24_scale"])
        # 同向：价格↑ OI↑ 的次数
        align_score = directional_score(up_up, neutral=0.0, scale=par["align_scale"])
    else:
        # 做空：希望 OI 下降（-oi24 越大越好）
        oi_score = directional_score(-oi24, neutral=0.0, scale=par["oi24_scale"])
        # 同向：价格↓ OI↑ 的次数（空头持仓增加）
        align_score = directional_score(dn_up, neutral=0.0, scale=par["align_scale"])

    # 加权平均
    O_raw = par["oi_weight"] * oi_score + par["align_weight"] * align_score

    # 拥挤度惩罚
    if crowding_warn:
        O_raw -= par["crowding_p95_penalty"]

    O = int(round(max(0.0, min(100.0, O_raw))))

    meta = {
        "oi1h_pct": round(oi1h * 100, 2),
        "oi24h_pct": round(oi24 * 100, 2),
        "dnup12": dn_up,
        "upup12": up_up,
        "crowding_warn": crowding_warn,
        "p95_oi24": round(p95 * 100, 2) if p95 is not None else None,
        "den": den,
        "oi_score": oi_score,
        "align_score": align_score,
        "data_source": "oi_data"
    }
    return O, meta